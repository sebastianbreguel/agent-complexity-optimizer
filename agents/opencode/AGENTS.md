# Complexity Optimizer

When asked to analyze, scan, audit, or review performance, find bottlenecks or inefficient code, or benchmark/profile code, follow this workflow.

## Core Rule

Optimize only when current behavior is understood and can be preserved. Scanner output = leads, not proof: confirm input size and call frequency, and measure when the code can run.

## Tools

```bash
python3 ~/.opencode/complexity-optimizer/analyze_complexity.py . --format markdown   # ranked hotspots + 0-100 health score
python3 ~/.opencode/complexity-optimizer/analyze_complexity.py . --changed main      # only files changed vs main
python3 ~/.opencode/complexity-optimizer/measure_growth.py "python3 bench.py {n}"  # measured growth: x2 per doubling = O(n), x4 = O(n^2)
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

Good and bad practices per language and domain (Python, JS/TS, React, Go, JVM, C#, Ruby, Rust, SQL/ORM, data pipelines, CI pipelines): https://github.com/sebastianbreguel/agent-complexity-optimizer/tree/main/skills/complexity-optimizer/references
