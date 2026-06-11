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

# Scanner install path per condensed agent (must match scripts/install.js destinations).
CONDENSED_TARGETS = {
    "agents/windsurf/.windsurfrules": "~/.codeium/windsurf/complexity-optimizer/analyze_complexity.py",
    "agents/cline/.clinerules": "~/.cline/complexity-optimizer/analyze_complexity.py",
    "agents/gemini/GEMINI.md": "~/.gemini/complexity-optimizer/analyze_complexity.py",
    "agents/opencode/AGENTS.md": "~/.opencode/complexity-optimizer/analyze_complexity.py",
    "agents/copilot/copilot-instructions.md": ".github/complexity-optimizer/analyze_complexity.py",
    "agents/aider/CONVENTIONS.md": "~/.aider/complexity-optimizer/analyze_complexity.py",
    "agents/amazon-q/.amazonq/rules/complexity-optimizer.md": "~/.amazonq/complexity-optimizer/analyze_complexity.py",
    "agents/zed/complexity-optimizer.md": "~/.config/zed/complexity-optimizer/analyze_complexity.py",
    "agents/cursor/complexity-optimizer.mdc": "~/.cursor/rules/complexity-optimizer/analyze_complexity.py",
}

CURSOR_FRONTMATTER = """---
description: Analyze codebase for algorithmic complexity hotspots and propose safe optimizations. Use when asked to find inefficient loops, N+1 queries, O(n^2) patterns, or reduce complexity.
globs:
alwaysApply: false
---

"""

CONDENSED_TEMPLATE = """# Complexity Optimizer

When asked to analyze, scan, audit, or review codebase complexity, follow this workflow.

## Core Rule

Optimize only when current behavior is understood and can be preserved. Small proven improvement with tests > broad rewrite.

## Scanner

Run first-pass analysis:
```bash
python3 {scanner_path} . --format markdown
```

Scanner output = leads, not proof. Inspect surrounding code for context.

## Default Report

Produce automatically when asked for analysis:

- Scope analyzed, stack/test commands detected
- Top findings ranked by impact
- Findings as a table, mandatory columns (never drop one): Location | Current pattern | Current (Cost) | Future | Impact | Risk | Recommended change
- Tests/benchmarks needed
- "No files modified" unless implementation requested

## Workflow

1. Baseline: language, framework, test/build commands, hot paths, existing tests.
2. Rank: hot paths first. Algorithmic complexity > constant factors.
3. Prove: tests for target function. Edge cases: empty, duplicates, ordering, nulls, errors, pagination.
4. Optimize: maps/sets for lookups, indexing for nested scans, memoization for renders, bulk fetch for N+1.
5. Verify: tests + lint/build, benchmark if non-obvious, report before/after.
6. Benchmark (post-implementation only): generate temp script measuring original vs optimized. Python: timeit + tracemalloc. JS/TS: performance.now + process.memoryUsage. Use project fixtures first, synthetic fallback. Delete temp scripts after. Skip with reason if env restricted.
7. Performance report: add `## Performance Benchmark` table (Function | Metric | Before | After | Delta | Change%). Auto-scale units. Include data source, iterations, runtime, dev-machine disclaimer.

## Safety

Before: data sizes matter? ordering preserved? identity safe? caches invalidated? auth/tenant preserved?
After: narrow test → broad suite → benchmark → localized patch.

## Common Transforms

- Nested lookup → map: O(a*b) → O(a+b)
- Membership in loop → Set: O(n*m) → O(n+m)
- Sort in loop → sort once: O(n^2 log n) → O(n log n)
- Pairwise → sort+two-pointer: O(n^2) → O(n log n)
- Render recompute → memoized selectors
- N+1 → bulk fetch / joins / dataloaders
"""

CONTINUE_TEMPLATE = """# Continue.dev Complexity Optimizer
# Add to .continue/config.yaml in your project or ~/.continue/config.yaml globally

customCommands:
  - name: complexity-report
    description: Analyze codebase for algorithmic complexity hotspots
    prompt: |
      Analyze this codebase for algorithmic complexity and performance hotspots.

      Run the scanner first:
      ```bash
      python3 ~/.continue/complexity-optimizer/analyze_complexity.py . --format markdown
      ```

      Then produce a report with:
      - Scope analyzed, stack/test commands detected
      - Top findings ranked by impact
      - Findings as a table, mandatory columns (never drop one): Location | Current pattern | Current (Cost) | Future | Impact | Risk | Recommended change
      - Tests/benchmarks needed

      Follow these rules:
      - Only edit files if I explicitly ask to implement/fix/optimize
      - Prefer maps/sets for lookups, indexing for nested scans, memoization for renders, bulk fetch for N+1
      - Verify: tests + lint/build, benchmark if non-obvious
      - Safety: preserve ordering, identity, auth/tenant constraints

      After implementing optimizations, benchmark the changes:
      - Generate a temp script measuring original vs optimized function (timeit+tracemalloc for Python, performance.now+process.memoryUsage for JS/TS)
      - Use project fixtures first, synthetic data as fallback
      - Report results in a Performance Benchmark table: Function | Metric | Before | After | Delta | Change%
      - Auto-scale units (μs/ms/s, KB/MB/GB), include data source and dev-machine disclaimer
      - Skip with reason if environment is restricted
"""


def generate() -> dict[Path, str]:
    source = SOURCE_SKILL.read_text(encoding="utf-8")
    files: dict[Path, str] = {}

    # Full-body targets: the Codex skill is a verbatim copy (scanner ships alongside it),
    # the Claude fallback command gets the scanner path rewritten to its install location.
    files[ROOT / "agents/codex/SKILL.md"] = source.replace(
        "Use when asked to scan files,", "Use when Codex is asked to scan many files,", 1
    )
    files[ROOT / "agents/claude/complexity-optimizer.md"] = source.replace(
        "scripts/analyze_complexity.py", "~/.claude/commands/complexity-optimizer/analyze_complexity.py"
    )

    for relpath, scanner_path in CONDENSED_TARGETS.items():
        body = CONDENSED_TEMPLATE.format(scanner_path=scanner_path)
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
