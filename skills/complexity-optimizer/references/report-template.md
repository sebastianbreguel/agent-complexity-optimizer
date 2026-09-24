# Report Template

Use this structure by default when asked for a complexity analysis, audit, scan, review, or report. Do not wait for the user to ask for these fields.

## Summary

- Scope analyzed (whole repo, a path, or `--changed <base>`):
- Stack detected:
- Test/build commands detected:
- Density: `<x>` score points per 1,000 lines from the scanner (lower is better; a trend, not a quality verdict), plus the baseline delta if one was used
- Highest-impact hotspot:
- Patch status: proposed / implemented / blocked
- Files modified: yes / no

## Top Functions

The scanner's hotspot table (function, location, score, patterns), trimmed to the ones that survived triage. For each dropped hotspot, one line on why (bounded n, one-off script, already batched).

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

After the table, for each finding add a short note covering:

- **Evidence:** where n comes from and how often the code runs; "measured" (profile, benchmark, query count) or "estimated".
- **Verdict:** confirmed, fixed, false positive, or won't fix, as recorded with `verdicts.py`.
- Why the pattern is costly, and why behavior should remain equivalent after the change.
- The tests or measurements still needed.

## Changes Made

- Files changed:
- Main algorithmic change:
- Complexity before:
- Complexity after:

## Verification

- Profile summary (function, self %, total %, callers) and the workload used:
- Tests run (the ones covering the edited code first):
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
| `function_name` | Growth exponent (`measure_growth.py`) | | | | |

- Benchmark command, sizes, and repeats:
- Before/after as ranges (min to max), not single numbers; a win needs 1.2x or more with non-overlapping ranges:
- Data source:
- Environment:

> Note: benchmarks ran on the development machine. Production numbers may differ based on hardware, load, and data volume.

If benchmark was skipped: "Benchmark skipped: [reason]. See theoretical complexity estimates in Findings above."

"No change recommended" is a valid result when the hotspot is under ~5% of the profile or the gain is within noise; say which.
