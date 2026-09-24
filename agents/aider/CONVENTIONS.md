# Complexity Optimizer

When asked to analyze, scan, audit, or review performance, find bottlenecks or inefficient code, or benchmark/profile code, follow this workflow.

## Core Rule

Optimize only when current behavior is understood and can be preserved. Scanner output = leads, not proof: confirm input size and call frequency, and measure when the code can run.

Quality bar: a better algorithm or data structure (Set/Map index, bulk query, bounded concurrency, one accumulator, one sort, vectorized ops) with code at least as readable as before, using idiomatic built-ins and library APIs. No obscure micro-optimizations (unrolling, cached length, bit tricks, index loops over clear comprehensions) without a measured gain on a hot path; if the faster version is much harder to read, report the trade-off with numbers instead of applying it.

## Tools

```bash
python3 ~/.aider/complexity-optimizer/analyze_complexity.py . --format markdown   # hotspots ranked by function
python3 ~/.aider/complexity-optimizer/analyze_complexity.py . --changed main      # only files changed vs main
python3 ~/.aider/complexity-optimizer/measure_growth.py "python3 bench.py {n}"  # measured growth exponent with a confidence interval
python3 ~/.aider/complexity-optimizer/verdicts.py add ~/.complexity-optimizer/verdicts/<repo>.jsonl "<path>::<function>::<kind>" confirmed
```

## Doctor Workflow

1. Baseline: stack, entry points, test/build commands.
2. Scan: read the top functions first, not the raw list.
3. Triage each hotspot: How big does n get (request payload, DB table, config constant)? How often does it run (per request/render/row, cron, one-off)? Is the fix cheap and safe? Drop bounded or one-off leads with a one-line reason.
4. Check what the scanner can't see: ORM lazy loading in loops/serializers, missing indexes (EXPLAIN ANALYZE), blocking I/O in async code, React re-render churn, row-by-row pandas, N+1 split across functions.
5. Confirm when the code can run: profile a representative workload and cross it with the hotspots (under ~5% of the time drops in priority), or measure_growth.py for the growth order. Record a verdict per hotspot examined (confirmed, fixed, false_positive, wont_fix).
6. Report: findings table with mandatory columns (never drop one): Location | Current pattern | Current (Cost) | Future | Impact | Risk | Recommended change. Add evidence per finding (measured vs estimated) and the tests needed. State "No files modified" unless implementation was requested.

## Optimize (only when asked)

All steps required: prove behavior with tests; profile first and work only on functions with at least ~5% of the time; one fix card per finding ("line L of f() does X per element of Y; do Z"); fix the structure (index, batch, bounded concurrency, vectorize), never global caches, monkey-patches or benchmark-shaped fast paths; run the tests covering the edit after each fix; benchmark before vs after (exact command, sizes, repeats, alternating fresh-process runs; a win needs 1.2x or more with non-overlapping ranges); re-profile and iterate up to 4-5 rounds, keeping the best measured variant. "No change" is a valid result when the gain is within noise. Then add a `## Performance Benchmark` table (Function | Metric | Before | After | Delta | Change%) with data source, runtime, and a dev-machine disclaimer. Skip with a reason if the environment is restricted.

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
