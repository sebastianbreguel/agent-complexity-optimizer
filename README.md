# agent-complexity-optimizer

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![npm](https://img.shields.io/npm/v/agent-complexity-optimizer)](https://www.npmjs.com/package/agent-complexity-optimizer)
[![Agents](https://img.shields.io/badge/agents-13+-green)](#supported-agents)
[![CI](https://github.com/sebastianbreguel/agent-complexity-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/sebastianbreguel/agent-complexity-optimizer/actions)

Scan any codebase for O(n^2) hotspots, N+1 queries, and algorithmic complexity issues. Get a structured report with severity, location, and fix suggestions — without modifying a single file.

Works as a skill/plugin for **13 AI coding agents**, or standalone via Python CLI.

> Extended from [codex-complexity-optimizer](https://github.com/Kappaemme-git/codex-complexity-optimizer) by [Kappaemme](https://github.com/Kappaemme-git). See [CREDITS.md](CREDITS.md) for full attribution and a breakdown of what this project adds.

## Demo

Given this code:

```python
def find_duplicates(users, transactions):
    duplicates = []
    for t in transactions:
        for u in users:                          # O(n*m) nested scan
            if u["id"] == t["user_id"]:
                duplicates.append(t)
    return duplicates

def get_user_orders(user_ids, db):
    results = []
    for uid in user_ids:
        order = db.query(f"SELECT * FROM orders WHERE user_id = {uid}")  # N+1
        results.append(order)
    return results
```

The scanner produces:

```
# Complexity Hotspots

## HIGH nested-loop
- Location: `example.py:4`
- Finding: Nested loop may create O(n^2) or worse behavior.
- Suggestion: Check whether a map/set index, sort+two-pointer pass,
  grouping, or batching can replace the inner scan.

## HIGH io-or-query-in-loop
- Location: `example.py:12`
- Finding: Potential database/API/file operation inside a loop.
- Suggestion: Look for N+1 behavior; batch or preload while preserving
  auth, filters, ordering, and error handling.
```

## What It Detects

| Pattern | Severity | Example |
|---------|----------|---------|
| Nested loops | High | `for x in A: for y in B` — O(n*m) |
| N+1 queries | High | `db.query()` / `fetch()` inside a loop |
| Sorting inside loops | High | `.sort()` called per iteration |
| Membership checks in loops | Medium | `.includes()`, `in`, `indexOf()` inside iteration |
| Render-path recomputation | Medium | `.filter().map()` in React component body |
| Pairwise comparisons | High | Every-pair scan that could be sort+sweep |

Supports: Python (AST-based), JavaScript, TypeScript, JSX/TSX, Java, Go, C, C++, C#, Ruby, PHP, Swift, Rust, Kotlin, Scala, Lua, Zig, Elixir, Erlang, Dart, R, Julia, OCaml, Clojure, and more (regex-based).

## Install

### Claude Code (marketplace)

```bash
/plugin marketplace add sebastianbreguel/agent-complexity-optimizer
/plugin install complexity-optimizer@complexity-optimizer
```

### Codex

```bash
npx skills add sebastianbreguel/agent-complexity-optimizer -a codex -g -y
```

### All other agents (auto-detect)

```bash
npx agent-complexity-optimizer
```

Auto-detects installed agents (Cursor, Windsurf, Copilot, Gemini CLI, Cline/Roo, Aider, OpenCode, Continue.dev, Amazon Q, Zed AI) and writes the correct config format for each. Preview with `--dry-run`.

### Standalone (no agent needed)

```bash
python3 skills/complexity-optimizer/scripts/analyze_complexity.py /path/to/repo --format markdown
python3 skills/complexity-optimizer/scripts/analyze_complexity.py /path/to/repo --format json
```

## Supported Agents

| Agent | Install | Config format |
|-------|---------|---------------|
| Claude Code | marketplace / `npx skills add` | SKILL.md |
| Codex (OpenAI) | `npx skills add` | SKILL.md + openai.yaml |
| Pi | `npm install -g` | SKILL.md (pi.skills) |
| Cursor | auto-detect | `.mdc` rule |
| Windsurf | auto-detect | `.windsurfrules` |
| GitHub Copilot | auto-detect | `copilot-instructions.md` |
| Gemini CLI | auto-detect | `GEMINI.md` |
| Cline / Roo Code | auto-detect | `.clinerules` |
| Aider | auto-detect | `CONVENTIONS.md` |
| OpenCode | auto-detect | `AGENTS.md` |
| Continue.dev | auto-detect | Custom command YAML |
| Amazon Q | auto-detect | Rules `.md` |
| Zed AI | auto-detect | Assistant rules |

## Usage

Ask your agent naturally:

```
Analyze this codebase for complexity hotspots and give me a report.
```

```
Scan for performance issues — nested loops, N+1 queries, O(n^2) patterns.
```

Reports are read-only by default. To apply a fix:

```
Implement the lowest-risk optimization from the report and run the tests.
```

## What This Project Adds

The [original project](https://github.com/Kappaemme-git/codex-complexity-optimizer) supported Codex only. This fork extends it to 13 agents and adds:

- **Universal installer** — auto-detects agents and writes native config formats
- **Claude Code marketplace** — first-class plugin support
- **Extended scanner** — additional languages (Rust, Kotlin, Scala, Lua, Zig, Elixir, Erlang, Dart, R, Julia, OCaml, Clojure) and patterns (list comprehensions, generator expressions, more query signatures)
- **Structured reports** — with severity ranking, benchmark sections, and safety checklists

## License

MIT
