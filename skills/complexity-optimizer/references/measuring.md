# Measuring Performance

Measure before and after every optimization. Static findings say where to look; measurements say whether it matters.

## Method

1. **Reproduce with realistic input.** Use production-like sizes (row counts, payload sizes, number of users). A quadratic loop over 20 items is not a bottleneck; over 50,000 it is.
2. **Profile to find where the time goes** before changing code. A sampling profiler shows the hot functions with low overhead; a tracing profiler shows exact call counts (useful to spot N+1: the same query 5,000 times). Prefer one that sees native frames (`py-spy record --native`): a pure-Python profiler can miss that most of the time is inside C code. Summarize it in at most 40 lines (function, self %, total %, caller chain) and check that the workload actually goes through the hotspot you're about to change.
3. **Benchmark the suspect** in isolation: warm up, repeat, report the minimum or median, keep the machine otherwise idle, and compare versions on the same machine and data.
4. **Check the growth order** with a doubling test: run sizes n, 2n, 4n, 8n. Time x2 per doubling means O(n), x4 means O(n^2), x8 means O(n^3).

   ```bash
   python3 scripts/measure_growth.py "python3 bench.py {n}" --sizes 2000 4000 8000 16000
   ```

   The script runs every size several times in a shuffled order, takes the median run, subtracts process startup (measured with n=0; pass `--startup-n 1` if 0 is invalid), and prints:
   - **Time exponent with a 95% confidence interval** from resampling the runs (bootstrap). When the interval spans two classes, the verdict says "inconclusive" and names both; add sizes or repeats.
   - **R²** of the log-log fit. Under 0.9 the cost isn't one power of n, so read the **local exponent** per size instead. A local exponent that keeps rising (for example n^2 hidden behind a large linear term) means the real order is at least the last value.
   - **Memory exponent** of the peak resident memory above startup (not on Windows). It only fits sizes that grow more than 10 MB above startup and can read about 0.1 too steep, because startup's own peak sits a few MB above what the process keeps; trust the class, and the number once growth reaches tens of MB.

   Sizes with under 50 ms of work beyond startup are left out of the fit; with fewer than two left it answers "Inconclusive" instead of guessing, so pick larger sizes.
5. **Measure memory** alongside time when the change trades one for the other (indexes, caches, precomputation): `measure_growth.py` reports how peak memory grows, and `/usr/bin/time -l <cmd>` on macOS or `/usr/bin/time -v <cmd>` on Linux reports one run's peak RSS (resident memory).
6. **Confirm in production data** when available: APM traces (Datadog, OpenTelemetry), slow query logs, `pg_stat_statements`, and error-rate or latency dashboards around the change.

## Whole Commands and Executions

| Goal | Command |
|------|---------|
| Compare two commands | `hyperfine --warmup 3 'old-cmd' 'new-cmd'` (add `--export-markdown out.md` for the report) |
| Time + peak memory | `/usr/bin/time -l cmd` (macOS), `/usr/bin/time -v cmd` (Linux) |
| Attach to a running process | `py-spy top --pid <pid>`, `rbspy record --pid <pid>`, `dotnet-trace collect -p <pid>`, `asprof -d 30 -f flame.html <pid>` (JVM) |
| Slowest tests | `pytest --durations=15`, `vitest --reporter=verbose`, `go test -json ./...` (look at `Elapsed`), `jest --verbose` |

## Per Language

| Language | Profile (where) | Benchmark (how much) |
|----------|-----------------|----------------------|
| Python | `py-spy record -o profile.svg -- python app.py`; `python -m cProfile -o out.prof app.py` then `python -m pstats out.prof` (`sort cumtime`, `stats 20`); `pyinstrument app.py`; memory: `memray run app.py` | `python -m timeit -s "setup" "stmt"`; `timeit.repeat()` in a script; `pytest-benchmark` |
| JavaScript / TypeScript (Node) | `node --cpu-prof app.js` (open the `.cpuprofile` in Chrome DevTools); `node --prof app.js` then `node --prof-process isolate-*.log`; `clinic flame -- node app.js`; `0x app.js` | `performance.now()` loops; `tinybench` or `mitata`; `vitest bench` |
| Browser / React | Chrome DevTools Performance panel; React DevTools Profiler ("Highlight updates when components render") | `<Profiler onRender>` timings; Lighthouse; `npx -y react-doctor@latest .` for React-specific issues |
| Go | `go test -bench=. -benchmem -cpuprofile cpu.out -memprofile mem.out` then `go tool pprof -top cpu.out` or `go tool pprof -http=:8080 cpu.out`; `net/http/pprof` in services | `go test -bench=. -benchmem -count=10 > new.txt` and `benchstat old.txt new.txt` |
| Java / Kotlin / Scala | async-profiler (`asprof -d 30 -f flame.html <pid>`); JDK Flight Recorder (`java -XX:StartFlightRecording=duration=60s,filename=rec.jfr ...`, open in JDK Mission Control) | JMH (`@Benchmark`); kotlinx-benchmark |
| C# / .NET | `dotnet-trace collect -p <pid>`; `dotnet-counters monitor -p <pid>`; Visual Studio / Rider profilers | BenchmarkDotNet with `[MemoryDiagnoser]` |
| Ruby | `stackprof`; `rbspy record -- ruby app.rb`; `rack-mini-profiler` in Rails | `benchmark-ips` |
| Rust | `cargo flamegraph`; `samply record ./target/release/app`; `perf record` / `perf report` on Linux | `criterion` with `cargo bench` (always `--release`) |
| SQL | `EXPLAIN (ANALYZE, BUFFERS) <query>` (PostgreSQL), `EXPLAIN ANALYZE` (MySQL 8.0.18+); `pg_stat_statements` for the most expensive queries | Run the query at production-like row counts; compare plans before and after an index |

## Reading the Results

- **Self time vs total time:** a function with high total but low self time is slow because of what it calls; follow the callees.
- **Many cheap calls add up:** 10,000 x 2 ms queries is 20 s. Count calls, not just their cost.
- **Wall time vs CPU time:** a large gap means waiting (I/O, locks, network). Batch or parallelize the waits instead of optimizing CPU code.
- **Noise:** identical programs can differ by 10% or more between runs. Alternate old and new runs, repeat at least 5 times each, and claim a win only at 1.2x or more with non-overlapping ranges, or use `benchstat` or hyperfine's statistics.
- **Benchmarks ran on the development machine.** Production numbers may differ with hardware, load, and data volume; say so in the report.
