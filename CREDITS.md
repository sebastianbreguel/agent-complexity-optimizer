# Credits

## Original Work

This project is based on [codex-complexity-optimizer](https://github.com/Kappaemme-git/codex-complexity-optimizer) by [Kappaemme](https://github.com/Kappaemme-git), which provided:

- The core Python complexity scanner (`analyze_complexity.py`)
- The optimization playbook and report template
- The Codex skill format (SKILL.md + openai.yaml)
- The npm installer pattern

Original project license: MIT

## What This Project Adds

This project extends the original Codex-only skill into a universal installer that works with every major AI coding agent:

| Agent | Format | Original |
|-------|--------|----------|
| Codex (OpenAI) | `SKILL.md` + `openai.yaml` | Yes (by Kappaemme) |
| Claude Code | Custom command `.md` | New |
| Cursor | `.mdc` rule | New |
| Windsurf (Codeium) | `.windsurfrules` | New |
| GitHub Copilot | `copilot-instructions.md` | New |
| Gemini CLI | `GEMINI.md` | New |
| Cline / Roo Code | `.clinerules` | New |
| Aider | `CONVENTIONS.md` | New |
| OpenCode | `AGENTS.md` | New |
| Continue.dev | `config.yaml` custom command | New |
| Amazon Q Developer | Rules `.md` | New |
| Zed AI | Assistant rules | New |

The Python scanner was extended with support for additional languages (Rust, Kotlin, Scala, Lua, Zig, Elixir, Erlang, Dart, R, Julia, OCaml, Clojure) and additional pattern detection (list comprehensions, generator expressions, more query patterns).
