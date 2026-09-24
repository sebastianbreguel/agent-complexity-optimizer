#!/usr/bin/env python3
"""Generate per-agent config files from the canonical skill definition.

Sources of truth:
- skills/complexity-optimizer/SKILL.md  -> full-body targets (Claude command, Codex skill)
- CONDENSED_TEMPLATE (below)            -> condensed targets (Cursor, Windsurf, Cline, ...)
- CONTINUE_TEMPLATE (below)             -> Continue.dev customCommands yaml

Static files (agents/codex/agents/openai.yaml, agents/aider/.aider.conf.yml) are
small pointers with no shared prose and are not generated.

Usage:
  python3 scripts/sync_agents.py            # rewrite all generated agent files
  python3 scripts/sync_agents.py --check    # exit 1 if any file is out of sync (CI)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_SKILL = ROOT / "skills" / "complexity-optimizer" / "SKILL.md"

# Tools directory per condensed agent: analyze_complexity.py, measure_growth.py and the
# complexity_scanner package are installed there (must match scripts/install.js destinations).
CONDENSED_TARGETS = {
    "agents/windsurf/.windsurfrules": "~/.codeium/windsurf/complexity-optimizer",
    "agents/cline/.clinerules": "~/.cline/complexity-optimizer",
    "agents/gemini/GEMINI.md": "~/.gemini/complexity-optimizer",
    "agents/opencode/AGENTS.md": "~/.opencode/complexity-optimizer",
    "agents/copilot/copilot-instructions.md": ".github/complexity-optimizer",
    "agents/aider/CONVENTIONS.md": "~/.aider/complexity-optimizer",
    "agents/amazon-q/.amazonq/rules/complexity-optimizer.md": "~/.amazonq/complexity-optimizer",
    "agents/zed/complexity-optimizer.md": "~/.config/zed/complexity-optimizer",
    "agents/cursor/complexity-optimizer.mdc": "~/.cursor/rules/complexity-optimizer",
}
CLAUDE_TOOLS_DIR = "~/.claude/complexity-optimizer"
REFERENCES_URL = "https://github.com/sebastianbreguel/agent-complexity-optimizer/tree/main/skills/complexity-optimizer/references"

CURSOR_FRONTMATTER = """---
description: Analyze codebase for algorithmic complexity hotspots and propose safe optimizations. Use when asked to find inefficient loops, N+1 queries, O(n^2) patterns, or reduce complexity.
globs:
alwaysApply: false
---

"""

CONDENSED_TEMPLATE = """# Complexity Optimizer

When asked to analyze, scan, audit, or review performance, find bottlenecks or inefficient code, or benchmark/profile code, follow this workflow.

## Core Rule

Optimize only when current behavior is understood and can be preserved. Scanner output = leads, not proof: confirm input size and call frequency, and measure when the code can run.

## Tools

```bash
python3 {tools_dir}/analyze_complexity.py . --format markdown   # ranked hotspots + 0-100 health score
python3 {tools_dir}/analyze_complexity.py . --changed main      # only files changed vs main
python3 {tools_dir}/measure_growth.py "python3 bench.py {{n}}"  # measured growth: x2 per doubling = O(n), x4 = O(n^2)
```

## Doctor Workflow

1. Baseline: stack, entry points, test/build commands.
2. Scan: read the health score and top functions first, not the raw list.
3. Triage each hotspot: How big does n get (request payload, DB table, config constant)? How often does it run (per request/render/row, cron, one-off)? Is the fix cheap and safe? Drop bounded or one-off leads with a one-line reason.
4. Check what the scanner can't see: ORM lazy loading in loops/serializers, missing indexes (EXPLAIN ANALYZE), blocking I/O in async code, React re-render churn, row-by-row pandas, N+1 split across functions.
5. Confirm with a profiler or measure_growth.py when the code can run.
6. Report: findings table with mandatory columns (never drop one): Location | Current pattern | Current (Cost) | Future | Impact | Risk | Recommended change. Add evidence per finding (measured vs estimated) and the tests needed. State "No files modified" unless implementation was requested.

## Optimize (only when asked)

Prove behavior with tests, optimize conservatively, run tests/lint/build, benchmark before vs after on the same machine and data (growth exponent plus speed/RAM), then add a `## Performance Benchmark` table (Function | Metric | Before | After | Delta | Change%) with data source, iterations, runtime, and a dev-machine disclaimer. Skip with a reason if the environment is restricted.

## Common Transforms

- Nested lookup -> map/set index: O(a*b) -> O(a+b)
- Query/API call per item -> bulk fetch, eager load, batch endpoint
- Sequential awaits -> Promise.all / asyncio.gather with a concurrency limit
- Spread / concat / pd.concat accumulation -> mutate one accumulator: O(n^2) -> O(n)
- String += in Java/C#/Go/Kotlin loops -> StringBuilder / strings.Builder
- pop(0) / shift() in loops -> deque
- Sort in loop -> sort once, heap for top-k
- Regex compile / deep copy per item -> hoist out of the loop
- Row-by-row pandas -> vectorized columns, merge, groupby
- Render-path filter/sort -> memoize, derive on the server, virtualize long lists

## Safety

Before: data sizes matter? ordering preserved? identity safe? caches invalidated? auth/tenant/pagination preserved? rate limits respected when parallelizing?
After: narrow test -> broad suite -> benchmark -> localized patch.

Good and bad practices per language and domain (Python, JS/TS, React, Go, JVM, C#, Ruby, Rust, SQL/ORM, data pipelines, CI pipelines): {references_url}
"""

CONTINUE_TEMPLATE = """# Continue.dev Complexity Optimizer
# Add to .continue/config.yaml in your project or ~/.continue/config.yaml globally

customCommands:
  - name: complexity-report
    description: Find performance bottlenecks and inefficient algorithms
    prompt: |
      Analyze this codebase for performance bottlenecks and algorithmic complexity.

      Run the scanner first (ranked hotspots + 0-100 health score):
      ```bash
      python3 ~/.continue/complexity-optimizer/analyze_complexity.py . --format markdown
      ```

      Then triage each top function: how big does n get, how often does it run, is the fix cheap and safe?
      Drop bounded or one-off leads with a one-line reason. Also check what the scanner can't see:
      ORM lazy loading, missing indexes, blocking I/O in async code, React re-renders, row-by-row pandas.

      Report:
      - Health score, scope analyzed, stack/test commands detected
      - Findings as a table, mandatory columns (never drop one): Location | Current pattern | Current (Cost) | Future | Impact | Risk | Recommended change
      - Evidence per finding (measured vs estimated) and the tests/benchmarks needed

      Follow these rules:
      - Only edit files if I explicitly ask to implement/fix/optimize
      - Prefer maps/sets for lookups, bulk fetches for N+1, bounded concurrency for sequential awaits, one accumulator instead of spread/concat
      - Safety: preserve ordering, identity, auth/tenant constraints, rate limits

      After implementing optimizations, benchmark the changes:
      - Growth order: python3 ~/.continue/complexity-optimizer/measure_growth.py "python3 bench.py {n}"
      - Speed/RAM: timeit + tracemalloc (Python), performance.now + process.memoryUsage (JS/TS)
      - Report a Performance Benchmark table: Function | Metric | Before | After | Delta | Change%
      - Include data source and a dev-machine disclaimer; skip with a reason if the environment is restricted
"""


def generate() -> dict[Path, str]:
    source = SOURCE_SKILL.read_text(encoding="utf-8")
    files: dict[Path, str] = {}

    # Full-body targets: the Codex skill is a verbatim copy (scanner ships alongside it),
    # the Claude fallback command gets the scanner path rewritten to its install location.
    files[ROOT / "agents/codex/SKILL.md"] = source.replace(
        "Use when asked to scan files,", "Use when Codex is asked to scan many files,", 1
    )
    files[ROOT / "agents/claude/complexity-optimizer.md"] = (
        source.replace("python3 scripts/", f"python3 {CLAUDE_TOOLS_DIR}/")
        .replace("`scripts/", f"`{CLAUDE_TOOLS_DIR}/")
        .replace("`references/", f"`{CLAUDE_TOOLS_DIR}/references/")
    )

    for relpath, tools_dir in CONDENSED_TARGETS.items():
        body = CONDENSED_TEMPLATE.format(tools_dir=tools_dir, references_url=REFERENCES_URL)
        if relpath.endswith(".mdc"):
            body = CURSOR_FRONTMATTER + body
        files[ROOT / relpath] = body

    files[ROOT / "agents/continue-dev/config.yaml"] = CONTINUE_TEMPLATE
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync per-agent config files from SKILL.md and templates.")
    parser.add_argument("--check", action="store_true", help="Report drift without writing; exit 1 if any file differs.")
    args = parser.parse_args()

    drifted: list[Path] = []
    for path, content in generate().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        drifted.append(path)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"  [synced] {path.relative_to(ROOT)}")

    if args.check and drifted:
        print("Agent config files out of sync with SKILL.md/templates:")
        for path in drifted:
            print(f"  {path.relative_to(ROOT)}")
        print("Run: python3 scripts/sync_agents.py")
        return 1
    if not drifted:
        print("All agent config files in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
