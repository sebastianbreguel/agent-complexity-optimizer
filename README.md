# agent-complexity-optimizer

Universal complexity optimizer for AI coding agents. Scans your codebase for algorithmic complexity hotspots (nested loops, N+1 queries, O(n^2) patterns) and produces safe optimization reports.

Works with **every major AI coding agent**: Claude Code, Codex, Pi, Cursor, Windsurf, GitHub Copilot, Gemini CLI, Cline/Roo Code, Aider, OpenCode, Continue.dev, Amazon Q Developer, and Zed AI.

Based on [codex-complexity-optimizer](https://github.com/Kappaemme-git/codex-complexity-optimizer) by [Kappaemme](https://github.com/Kappaemme-git). See [CREDITS.md](CREDITS.md) for full attribution.

## Install

### Claude Code

```bash
npx skills add sebastianbreguel/agent-complexity-optimizer -a claude-code -g -y
```

### Codex

```bash
npx skills add sebastianbreguel/agent-complexity-optimizer -a codex -g -y
```

### Pi

Pi loads skills from npm packages with `pi.skills` metadata:

```bash
npm install -g agent-complexity-optimizer
```

### All other agents (auto-detect)

```bash
npx agent-complexity-optimizer
```

The fallback installer auto-detects which agents you have (Cursor, Windsurf, Copilot, Gemini CLI, Cline/Roo, Aider, OpenCode, Continue.dev, Amazon Q, Zed AI) and installs the right format for each.

Use `--dry-run` to preview:

```bash
npx agent-complexity-optimizer --dry-run
```

## Supported Agents

| Agent | Install method | Config format |
|-------|---------------|--------------|
| Claude Code | `npx skills add` | SKILL.md (slash command) |
| Codex (OpenAI) | `npx skills add` | SKILL.md + openai.yaml |
| Pi | npm install (pi.skills) | SKILL.md |
| Cursor | auto-detect installer | `.mdc` rule |
| Windsurf (Codeium) | auto-detect installer | `.windsurfrules` |
| GitHub Copilot | auto-detect installer | `copilot-instructions.md` |
| Gemini CLI | auto-detect installer | `GEMINI.md` |
| Cline / Roo Code | auto-detect installer | `.clinerules` |
| Aider | auto-detect installer | `CONVENTIONS.md` |
| OpenCode | auto-detect installer | `AGENTS.md` |
| Continue.dev | auto-detect installer | Custom command YAML |
| Amazon Q Developer | auto-detect installer | Rules `.md` |
| Zed AI | auto-detect installer | Assistant rules |

## Use

Ask your agent to analyze your codebase. The phrasing doesn't matter much:

```
Analyze this codebase for complexity hotspots and give me a report.
```

```
Scan this repo for performance issues — nested loops, N+1 queries, O(n^2) patterns.
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
python3 skills/complexity-optimizer/scripts/analyze_complexity.py /path/to/repo --format markdown
python3 skills/complexity-optimizer/scripts/analyze_complexity.py /path/to/repo --format json
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

1. Copy `skills/complexity-optimizer/scripts/analyze_complexity.py` to your agent's config directory
2. Copy the matching instruction file from `agents/<agent-name>/`
3. Follow your agent's docs for loading custom rules/instructions

## License

MIT. See [CREDITS.md](CREDITS.md) for attribution to the original project.
