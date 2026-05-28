# Report Template

Use this structure by default when asked for a complexity analysis, audit, scan, review, or report. Do not wait for the user to ask for these fields.

## Summary

- Scope analyzed:
- Stack detected:
- Test/build commands detected:
- Highest-impact hotspot:
- Patch status: proposed / implemented / blocked
- Files modified: yes / no

## Findings

Always render findings as a table with these exact columns, in this order. Never drop a column; use `—` when a value is unknown.

| # | Location | Current pattern | Current (Cost) | Future | Impact | Risk | Recommended change |
|---|----------|-----------------|----------------|--------|--------|------|--------------------|
| 1 | `file.py:120` | nested mask-max per group | O(N²) | O(N) | High | Low | replace with a single groupby |

Column meaning:

- **Location**: `file:line`.
- **Current pattern**: the existing construct (e.g. nested scan, repeated lookup, N+1 query).
- **Current (Cost)**: estimated complexity of the existing code.
- **Future**: estimated complexity after the recommended change.
- **Impact**: expected payoff (High / Medium / Low), given hot path and input size.
- **Risk**: chance of changing observable behavior (High / Medium / Low).
- **Recommended change**: the concrete transformation.

After the table, for each finding add a short note covering why the pattern is costly, why behavior should remain equivalent, and the tests or measurements needed.

## Changes Made

- Files changed:
- Main algorithmic change:
- Complexity before:
- Complexity after:

## Verification

- Tests run:
- Build/type/lint run:
- Benchmark or measurement:
- Residual risk:

## Performance Benchmark

> Only included when optimizations were implemented and benchmarks ran successfully.

For each optimized function:

| Function | Metric | Before | After | Delta | Change |
|----------|--------|--------|-------|-------|--------|
| `function_name` | Speed | | | | % |
| `function_name` | RAM | | | | % |

- Data source:
- Iterations:
- Environment:

> Note: benchmarks ran on the development machine. Production numbers may differ based on hardware, load, and data volume.

If benchmark was skipped: "Benchmark skipped: [reason]. See theoretical complexity estimates in Findings above."
