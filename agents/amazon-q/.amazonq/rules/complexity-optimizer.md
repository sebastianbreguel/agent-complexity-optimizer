# Complexity Optimizer

When asked to analyze, scan, audit, or review codebase complexity, follow this workflow.

## Core Rule

Optimize only when current behavior is understood and can be preserved. Small proven improvement with tests > broad rewrite.

## Scanner

Run first-pass analysis:
```bash
python3 ~/.amazonq/complexity-optimizer/analyze_complexity.py . --format markdown
```

## Default Report

- Scope analyzed, stack/test commands detected
- Top findings ranked by impact
- File:line, current pattern, why costly
- Current complexity → recommended change → new complexity
- Risk level, tests/benchmarks needed
- "No files modified" unless implementation requested

## Workflow

1. Baseline: language, framework, test/build commands, hot paths, existing tests.
2. Rank: hot paths first. Algorithmic complexity > constant factors.
3. Prove: tests for target function. Edge cases: empty, duplicates, ordering, nulls, errors.
4. Optimize: maps/sets for lookups, indexing for nested scans, memoization for renders, bulk fetch for N+1.
5. Verify: tests + lint/build, benchmark if non-obvious, report before/after.

## Common Transforms

- Nested lookup → map: O(a*b) → O(a+b)
- Membership in loop → Set: O(n*m) → O(n+m)
- Sort in loop → sort once: O(n^2 log n) → O(n log n)
- N+1 → bulk fetch / joins / dataloaders
