---
name: complexity-optimizer
description: Find and fix performance bottlenecks and inefficient algorithms in any codebase. Scans for O(n^2) loops, N+1 queries, sequential awaits, quadratic accumulation, repeated sorts/searches and render-path waste; ranks the functions most likely to be slow with a 0-100 health score; confirms with profilers and growth benchmarks; and optimizes safely without breaking behavior. Use when asked to scan or audit performance, find bottlenecks or inefficient code, review a slow endpoint, job, pipeline or CI run, benchmark or profile code, review a diff for performance, or reduce complexity (e.g. O(n^2) to O(n log n) / O(n)).
---

# Complexity Optimizer

## Core Rule

Optimize only when the current behavior is understood and can be preserved. Prefer a small, proven improvement with tests over a broad rewrite with unclear correctness. Scanner output is a lead, never proof: a bottleneck is confirmed by input size, call frequency, and ideally a measurement.

## Pick the Mode

| Request | Mode | Start with |
|---------|------|------------|
| "scan / audit / report / find bottlenecks" | Doctor report | Scanner on the repo, then triage |
| "X is slow" (endpoint, job, function, command) | Targeted diagnosis | Reproduce and profile X, then scan the files on its path |
| "review this PR / diff for performance" | Diff review | `--changed main`, then triage only the new findings |
| "CI / build / tests are slow" | Pipeline audit | `~/.claude/complexity-optimizer/references/domains/ci-pipelines.md` |
| "ETL / data job / notebook is slow" | Pipeline audit | `~/.claude/complexity-optimizer/references/domains/data-pipelines.md`, then scan |
| "optimize / fix / implement" | Optimize | A report first, then the optimize workflow |

Only edit files when the user asks to implement, fix, optimize, apply, change, or refactor. Analysis and reports never modify files, and say so.

## Doctor Workflow (default)

1. **Baseline.** Identify languages, frameworks, entry points, test/build/lint commands, and how the code runs in production (request handlers, workers, cron, UI).
2. **Scan.** Run the bundled scanner from this skill's directory:

   ```bash
   python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo> --format json   # or --format markdown
   ```

   Read `health` and `hotspots` (functions ranked by total score) first, then the findings. Do not paste the raw list.
3. **Triage every top hotspot** with three questions, reading the surrounding code:
   - **How big does n get?** Trace where each collection comes from: request payload, DB table, file, API page, or a fixed config constant.
   - **How often does it run?** Per request, per render, per message, per row, nightly cron, or one-off script.
   - **Is the fix cheap and safe?** Look for existing indexes, caches, batching helpers, or bulk endpoints to reuse.

   Drop leads whose n is small and bounded or whose path runs once, and say why in one line. A finding in a hot path with unbounded n stays, even if the fix is hard.
4. **Apply the heuristics the scanner cannot prove.** Open the matching `~/.claude/complexity-optimizer/references/languages/<language>.md` and `~/.claude/complexity-optimizer/references/domains/<domain>.md` and check the hot files for those patterns (ORM lazy loading, missing indexes, re-render churn, dtype and copy costs, blocking I/O on async paths, cross-function N+1 where the loop and the query live in different functions).
5. **Confirm when the code can run.** Profile the slow path, or benchmark the function at growing sizes with `~/.claude/complexity-optimizer/measure_growth.py` to show its real growth order (see `~/.claude/complexity-optimizer/references/measuring.md`). A measurement beats any estimate; say which findings are measured and which are estimated.
6. **Report** with `~/.claude/complexity-optimizer/references/report-template.md`: health score, ranked findings table, evidence per finding, and the measurements or checks still needed.

## Optimize Workflow (only when asked)

1. **Prove behavior.** Locate or add focused tests for the function being changed. Cover empty input, duplicates, ordering stability, null/missing values, errors, permissions, pagination, time zones, and mutation side effects. If behavior is ambiguous and untested, ask before changing semantics.
2. **Snapshot the original** for the before/after benchmark: inline the original function into the benchmark script; fall back to `git stash` only when imports make inlining impractical.
3. **Optimize conservatively** using `~/.claude/complexity-optimizer/references/optimization-playbook.md`: index with a map/set, batch or preload queries, run independent awaits concurrently with a limit, accumulate in place, sort once, memoize derived render data. Keep the patch localized.
4. **Verify.** Run the narrow test first, then the broader test/type/lint/build commands.
5. **Benchmark before vs after** on the same machine and data:
   - Growth order: `python3 ~/.claude/complexity-optimizer/measure_growth.py "<command with {n}>" --sizes 1000 2000 4000 8000` for both versions.
   - Absolute speed and memory: Python `timeit.repeat()` (min of 5 rounds) and `tracemalloc`; JS/TS `performance.now()` over many iterations and `process.memoryUsage().heapUsed`; other languages per `~/.claude/complexity-optimizer/references/measuring.md`.
   - Test data: project fixtures first (`tests/`, `fixtures/`, `__tests__/`, `test_data/`, `spec/`), otherwise synthetic data large enough to show the difference (10,000+ elements for quadratic patterns).
   - Write temporary benchmark scripts to a temp directory and delete them afterwards. If benchmarking is impossible, write "Benchmark skipped: [reason]" and keep the theoretical estimate.
6. **Report** the performance section of the template: before/after table, growth exponents, data source, iterations, runtime version, and the dev-machine disclaimer.

## Scanner Reference

```bash
python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo>                          # markdown report
python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo> --format json            # for tools and agents
python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo> --changed main           # only files changed vs main
python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo> --write-baseline b.json  # save today's findings
python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo> --baseline b.json --fail-on high  # CI: fail only on new ones
```

- **Selection:** respects `.gitignore`; skips tests (`--include-tests` to add them), generated and minified files. Migrations, seeds, scripts and examples are reported but ranked lower (`context: one-off`).
- **Score** = pattern weight x loop depth x confidence. **Health** = 100 / (1 + density / 25), where density is score points per 1,000 scanned lines: 50 means 25 points per 1,000 lines.
- **Confidence:** Python is parsed with its AST (`high`); other languages use line heuristics (`low`), so read their context before trusting them.
- **Suppress** a reviewed line with a trailing comment `complexity: ignore (reason)`.
- **Patterns:** `io-or-query-in-loop`, `await-in-loop`, `quadratic-accumulation`, `nested-loop`, `sort-in-loop`, `string-concat-in-loop`, `list-shift-in-loop`, `dataframe-row-loop`, `membership-in-loop`, `deep-copy-in-loop`, `repeated-scan`, `regex-compile-in-loop`, `render-derived-work`.
- **Blind spots:** it does not know types, input sizes, or call frequency; it cannot follow calls across functions (a loop calling a helper that queries); it cannot see ORM lazy loading through attribute access, exponential recursion, or missing indexes. Step 4 of the doctor workflow covers these.

If the scanner reports nothing, still inspect the known hot paths manually.

## Optimization Safety Checklist

Before editing:

- The data is large enough, or the code hot enough, for the complexity to matter.
- Output ordering is preserved where callers may rely on it.
- Object identity, mutability, and reference sharing are not part of the public behavior.
- Caches have a valid invalidation strategy.
- Deduplication does not collapse distinct records that share a display label.
- Batched queries keep tenant, permission, soft-delete, pagination, and sorting constraints.
- Concurrent calls respect rate limits, transactions, and ordering requirements.

After editing:

- Narrow test first, then the broadest relevant test/build command.
- Before/after benchmark numbers when a benchmark exists or was added.
- The patch is localized, with no formatting churn in unrelated files.

## References

- `~/.claude/complexity-optimizer/references/optimization-playbook.md`: transformations per pattern, with correctness checks.
- `~/.claude/complexity-optimizer/references/measuring.md`: profiling, benchmarking, growth tests, and how to read the results.
- `~/.claude/complexity-optimizer/references/languages/`: good and bad practices per language (Python, JavaScript/TypeScript, React, Go, JVM, C#, Ruby, Rust).
- `~/.claude/complexity-optimizer/references/domains/`: data access (SQL/ORM), data pipelines, CI pipelines.
- `~/.claude/complexity-optimizer/references/report-template.md`: the report format.
