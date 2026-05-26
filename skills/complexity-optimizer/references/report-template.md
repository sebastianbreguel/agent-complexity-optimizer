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

For each finding:

- Location:
- Current pattern:
- Estimated current complexity:
- Recommended change:
- Estimated complexity after:
- Why behavior should remain equivalent:
- Risk level:
- Tests or measurements needed:

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
