# agent-complexity-optimizer

Universal complexity optimizer for AI coding agents. Scans your codebase for algorithmic complexity hotspots (nested loops, N+1 queries, O(n^2) patterns) and produces safe optimization reports.

Works with **every major AI coding agent**: Claude Code, Codex, Cursor, Windsurf, GitHub Copilot, Gemini CLI, Cline/Roo Code, Aider, OpenCode, Continue.dev, Amazon Q Developer, and Zed AI.

Based on [codex-complexity-optimizer](https://github.com/Kappaemme-git/codex-complexity-optimizer) by [Kappaemme](https://github.com/Kappaemme-git). See [CREDITS.md](CREDITS.md) for details.

## Install

```bash
npm install -g agent-complexity-optimizer
```

The installer auto-detects which agents you have and installs the right format for each.

Or run without installing:

```bash
npx agent-complexity-optimizer
```

Use `--dry-run` to preview what would be installed:

```bash
npx agent-complexity-optimizer --dry-run
```

## Supported Agents

| Agent | Config format | Install location |
|-------|--------------|-----------------|
| Codex (OpenAI) | `SKILL.md` | `~/.codex/skills/complexity-optimizer/` |
| Claude Code | Custom command | `~/.claude/commands/complexity-optimizer/` |
| Cursor | `.mdc` rule | `~/.cursor/rules/` |
| Windsurf | `.windsurfrules` | `~/.codeium/windsurf/complexity-optimizer/` |
| GitHub Copilot | `copilot-instructions.md` | `~/.github/complexity-optimizer/` |
| Gemini CLI | `GEMINI.md` | `~/.gemini/complexity-optimizer/` |
| Cline / Roo Code | `.clinerules` | `~/.cline/complexity-optimizer/` |
| Aider | `CONVENTIONS.md` | `~/.aider/complexity-optimizer/` |
| OpenCode | `AGENTS.md` | `~/.opencode/complexity-optimizer/` |
| Continue.dev | Custom command YAML | `~/.continue/complexity-optimizer/` |
| Amazon Q | Rules `.md` | `~/.amazonq/complexity-optimizer/` |
| Zed AI | Assistant rules | `~/.config/zed/complexity-optimizer/` |

## Use

Ask your agent to analyze your codebase. The phrasing doesn't matter much — all agents understand the intent:

```
Analyze this codebase for complexity hotspots and give me a report.
```

```
Scan this repo for performance issues — nested loops, N+1 queries, O(n^2) patterns.
```

```
Find the worst algorithmic complexity in this project and suggest fixes.
```

For Codex specifically:

```
Use $complexity-optimizer to analyze this codebase and give me a full complexity report.
```

By default, reports don't modify files. To apply a fix:

```
Implement the lowest-risk optimization from the report and run the tests.
```

## Standalone Scanner

The Python scanner works independently of any agent:

```bash
python3 core/scripts/analyze_complexity.py /path/to/repo --format markdown
python3 core/scripts/analyze_complexity.py /path/to/repo --format json
```

Supports: Python, JavaScript, TypeScript, JSX/TSX, Java, Go, C, C++, C#, Ruby, PHP, Swift, Rust, Kotlin, Scala, Lua, Zig, Elixir, Erlang, Dart, R, Julia, OCaml, Clojure, and more.

## What It Detects

- **Nested loops** — O(n^2) or worse from scanning B for each item in A
- **Membership checks in loops** — `includes()`, `indexOf()`, `in` inside iteration
- **Sorting inside loops** — repeated O(n log n) work
- **N+1 queries** — database/API calls inside loops
- **Render-path recomputation** — expensive transforms in UI component render paths
- **Pairwise comparisons** — every-pair scans that could be sort+sweep

## Manual Install

If the auto-installer doesn't detect your agent, copy files manually:

1. Copy `core/scripts/analyze_complexity.py` to your agent's config directory
2. Copy the matching instruction file from `agents/<agent-name>/`
3. Follow your agent's docs for loading custom rules/instructions

## License

MIT. See [CREDITS.md](CREDITS.md) for attribution.
