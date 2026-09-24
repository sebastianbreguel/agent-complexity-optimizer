---
name: complexity-optimizer
description: Find and fix performance bottlenecks and inefficient algorithms in any codebase. Scans for O(n^2) loops, N+1 queries, sequential awaits, quadratic accumulation, repeated sorts/searches and render-path waste; ranks the functions most likely to be slow; confirms with profilers and growth benchmarks; and optimizes safely without breaking behavior. Use when asked to scan or audit performance, find bottlenecks or inefficient code, review a slow endpoint, job, pipeline or CI run, benchmark or profile code, review a diff for performance, or reduce complexity (e.g. O(n^2) to O(n log n) / O(n)).
---

# Complexity Optimizer

## Core Rule

Optimize only when the current behavior is understood and can be preserved. Prefer a small, proven improvement with tests over a broad rewrite with unclear correctness. Scanner output is a lead, never proof: a bottleneck is confirmed by input size, call frequency, and ideally a measurement.

## Quality Bar: Better Algorithm, Not Uglier Code

An optimization improves the algorithm or the data structure, and the result reads at least as clearly as the original:

- **Change the shape of the work, not the style of the code:** a `Set`/`Map`/dict index instead of a nested scan, one bulk query instead of one per item, bounded concurrency instead of sequential awaits, one accumulator instead of copies, one sort instead of many, a vectorized column expression instead of a row loop.
- **Use the idiomatic tool:** built-ins, the standard library, ORM batch/eager-loading APIs, vectorized libraries. Don't hand-roll a structure the language already has.
- **Name the new step:** an index or batch built before the loop gets a name that says what it is (`users_by_id`, `orders_by_customer`); extract a small, well-named helper when it clarifies intent.
- **Reject micro-optimizations that obscure intent** unless a measurement shows a relevant gain on a hot path: manual loop unrolling, caching `.length`, bit tricks, replacing clear comprehensions or `map`/`filter` with index loops, inlining helpers, premature object pooling.
- **When the only faster version is much harder to read,** don't apply it silently: report the trade-off with numbers (time saved, input size, how often it runs) and let the user decide.

## Pick the Mode

| Request | Mode | Start with |
|---------|------|------------|
| "scan / audit / report / find bottlenecks" | Doctor report | Scanner on the repo, then triage |
| "X is slow" (endpoint, job, function, command) | Targeted diagnosis | Reproduce and profile X, then scan the files on its path |
| "review this PR / diff for performance" | Diff review | Baseline from `main`, then `--changed main --baseline` to list only the findings the branch adds |
| "CI / build / tests are slow" | Pipeline audit | `~/.claude/complexity-optimizer/references/domains/ci-pipelines.md` |
| "ETL / data job / notebook is slow" | Pipeline audit | `~/.claude/complexity-optimizer/references/domains/data-pipelines.md`, then scan |
| "optimize / fix / implement" | Optimize | A report first, then the optimize workflow |

Only edit files when the user asks to implement, fix, optimize, apply, change, or refactor. Analysis and reports never modify project files, and say so (verdicts go to `~/.complexity-optimizer/`, outside the repo).

## Doctor Workflow (default)

1. **Baseline.** Identify languages, frameworks, entry points, test/build/lint commands, and how the code runs in production (request handlers, workers, cron, UI).
2. **Scan.** Run the bundled scanner from this skill's directory:

   ```bash
   python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo> --format json   # or --format markdown
   ```

   Read `hotspots` (functions ranked by their strongest finding) first, then the findings. Do not paste the raw list.
3. **Triage every top hotspot** with three questions, reading the surrounding code:
   - **How big does n get?** Trace where each collection comes from: request payload, DB table, file, API page, or a fixed config constant.
   - **How often does it run?** Per request, per render, per message, per row, nightly cron, or one-off script.
   - **Is the fix cheap and safe?** Look for existing indexes, caches, batching helpers, or bulk endpoints to reuse.

   Drop leads whose n is small and bounded or whose path runs once, and say why in one line. A finding in a hot path with unbounded n stays, even if the fix is hard. Record a verdict for every hotspot you examine (see Verdicts below).
4. **Apply the heuristics the scanner cannot prove.** Open the matching `~/.claude/complexity-optimizer/references/languages/<language>.md` and `~/.claude/complexity-optimizer/references/domains/<domain>.md` and check the hot files for those patterns (ORM lazy loading, missing indexes, re-render churn, dtype and copy costs, blocking I/O on async paths, cross-function N+1 where the loop and the query live in different functions).
5. **Confirm when the code can run.** Profile a representative workload and cross the profile with the hotspots: a hotspot under ~5% of the total time drops in priority, and a profile hotspot with no finding is a blind spot of the scanner worth listing. Benchmark a suspect at growing sizes with `~/.claude/complexity-optimizer/measure_growth.py` to show its real growth order (see `~/.claude/complexity-optimizer/references/measuring.md`). A measurement beats any estimate; say which findings are measured and which are estimated.
6. **Report** with `~/.claude/complexity-optimizer/references/report-template.md`: ranked findings table, evidence per finding, verdicts, and the measurements or checks still needed.

## Optimize Workflow (only when asked)

Every step is required. In agent studies, most of the possible gain was lost by editing the wrong function, and a mandatory profile and before/after benchmark were the changes that raised success the most.

1. **Prove behavior.** Locate or add focused tests for the function being changed. Cover empty input, duplicates, ordering stability, null/missing values, errors, permissions, pagination, time zones, and mutation side effects. If behavior is ambiguous and untested, ask before changing semantics.
2. **Profile first.** Run a sampling profiler that sees native frames (`py-spy record --native`, `perf`, async-profiler, `go tool pprof`; see `~/.claude/complexity-optimizer/references/measuring.md`) on a workload that goes through the hotspot, and write a summary of at most 40 lines: function, self %, total %, caller chain. Work only on functions with at least ~5% of the total. If the code can't run here, say so: every gain after this point is an estimate.
3. **Snapshot the original** for the before/after benchmark: inline the original function into the benchmark script; fall back to `git stash` only when imports make inlining impractical.
4. **Write one fix card per finding:** "line L of `f()` does X for each element of Y; do Z", plus the one before/after example for that pattern from `~/.claude/complexity-optimizer/references/optimization-playbook.md`. Don't load generic strategy lists.
5. **Fix the structure, locally,** following the quality bar above: lower the cost per element (index, batch, bounded concurrency, vectorize, one accumulator). No global caches, monkey-patches, stack introspection, or fast paths shaped like the benchmark. A design-level change (new service, schema, architecture) is reported, not applied. Review the diff for readability before calling it done.
6. **Verify after each fix.** Run the tests that cover the edited code first, then the broader test/type/lint/build commands. A failing test voids the speedup.
7. **Benchmark before vs after** on the same machine and data, and write down the exact command, sizes, and repeats:
   - Growth order: `python3 ~/.claude/complexity-optimizer/measure_growth.py "<command with {n}>"` for both versions; compare the exponents and their confidence intervals.
   - Absolute speed: alternate old and new runs, at least 5 of each, each in a fresh process, on at least 2 sizes (one not used while developing). Claim a win only at 1.2x or more with non-overlapping ranges (min to max); smaller differences are noise unless a randomized A/B shows otherwise.
   - Memory: `measure_growth.py` prints the peak-memory exponent; in-process, Python `tracemalloc`, JS `process.memoryUsage().heapUsed`, others per `~/.claude/complexity-optimizer/references/measuring.md`.
   - Test data: project fixtures first (`tests/`, `fixtures/`, `__tests__/`, `test_data/`, `spec/`), otherwise synthetic data large enough to show the difference (10,000+ elements for quadratic patterns).
   - Write temporary benchmark scripts to a temp directory and delete them afterwards. If benchmarking is impossible, write "Benchmark skipped: [reason]" and keep the theoretical estimate.
8. **Iterate until it flattens.** Profile again and continue while the same function still dominates or the exponent hasn't dropped, for at most 4-5 rounds. Keep the best measured variant, not the last one.
9. **"No change" is a valid result.** If the hotspot is under ~5% of the profile or the gain is within noise, say so and don't ship the edit.
10. **Sweep siblings and record verdicts.** After a confirmed fix, look for the same pattern elsewhere (filter the JSON findings by `kind`), and record `fixed` / `confirmed` / `false_positive` / `wont_fix` for each finding you examined.
11. **Report** the performance section of the template: profile summary, before/after table with ranges, growth exponents, tests run, data source, runtime version, and the dev-machine disclaimer.

## Scanner Reference

```bash
python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo>                          # markdown report
python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo> --format json            # for tools and agents
python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo> --changed main           # only files changed vs main
python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo> --write-baseline b.json  # save today's findings
python3 ~/.claude/complexity-optimizer/analyze_complexity.py <repo> --baseline b.json --fail-on high  # CI: fail only on new ones; new findings listed first
```

`--changed` selects whole files, so old findings in a touched file show up too. To see only what a branch introduces, write the baseline from `main` in a separate worktree and compare:

```bash
git worktree add /tmp/base main
python3 ~/.claude/complexity-optimizer/analyze_complexity.py /tmp/base --write-baseline /tmp/base.json
python3 ~/.claude/complexity-optimizer/analyze_complexity.py . --changed main --baseline /tmp/base.json   # findings tagged NEW
git worktree remove /tmp/base
```

- **Selection:** respects `.gitignore`; skips tests (`--include-tests` to add them), files marked `@generated` / `Code generated ... DO NOT EDIT` / `<auto-generated`, and minified files (mostly lines over 1,000 characters), listed in `generated_files`. Migrations, seeds, scripts and examples are reported but ranked lower (`context: one-off`).
- **Score** = pattern weight x loop depth x confidence. A hotspot scores its strongest finding plus 10% per extra distinct pattern: findings in one function are correlated evidence, so they aren't summed.
- **Density** = score points per 1,000 scanned lines. Lower is better and it tracks progress over time, but it is not a quality verdict: no study ties this kind of density to real slowness. It is omitted with `--changed`, where a few files aren't comparable with the whole repo.
- **Confidence:** Python is parsed with its AST (`high`); other languages use line heuristics (`low`), so read their context before trusting them.
- **Suppress** a reviewed line with a trailing comment `complexity: ignore (reason)`.
- **Patterns:** `io-or-query-in-loop`, `await-in-loop`, `quadratic-accumulation`, `nested-loop`, `sort-in-loop`, `string-concat-in-loop`, `list-shift-in-loop`, `dataframe-row-loop`, `membership-in-loop`, `deep-copy-in-loop`, `repeated-scan`, `regex-compile-in-loop`, `render-derived-work`.
- **Blind spots:** it does not know types, input sizes, or call frequency; it cannot follow calls across functions (a loop calling a helper that queries); it cannot see ORM lazy loading through attribute access, exponential recursion, or missing indexes. Step 4 of the doctor workflow covers these.

If the scanner reports nothing, still inspect the known hot paths manually.

### Verdicts

Weights are judgment calls until verdicts measure each rule's precision. Record one per finding you triage or fix, in a file per repo outside the repo:

```bash
python3 ~/.claude/complexity-optimizer/verdicts.py add ~/.complexity-optimizer/verdicts/<repo>.jsonl "<path>::<function>::<kind>" confirmed  # or fixed, false_positive, wont_fix
python3 ~/.claude/complexity-optimizer/verdicts.py report ~/.complexity-optimizer/verdicts/*.jsonl   # precision per rule and language
```

`confirmed` and `fixed` count as useful; `false_positive` and `wont_fix` (real but not worth changing) don't. A finding that just disappeared from a later scan is not a verdict. With 10 or more verdicts, a rule whose not-useful rate is likely over 10% goes on probation and over 25% is flagged off.

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
