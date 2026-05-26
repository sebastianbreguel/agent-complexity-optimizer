---
name: complexity-optimizer
description: Analyze a software codebase for algorithmic complexity and performance hotspots, then propose or implement safe optimizations without breaking behavior. Use when asked to scan files, find inefficient loops, nested iteration, repeated scans, costly rendering/recomputation, N+1 queries, avoidable O(n^2) or O(n) operations, or reduce complexity such as O(n^2) to O(n log n) / O(n), while preserving tests, APIs, outputs, and maintainability.
---

# Complexity Optimizer

## Core Rule

Optimize only when the current behavior is understood and can be preserved. Prefer a small, proven improvement with tests over a broad rewrite with unclear correctness.

## Default Behavior

When asked to analyze, scan, audit, review, or "give me a report" for a codebase, produce the full complexity report automatically.

Default report contents:

- Scope analyzed and detected stack/test commands.
- Top findings ranked by likely impact.
- File and line for each finding.
- Current pattern and why it may be costly.
- Estimated current complexity.
- Recommended change.
- Estimated complexity after the change.
- Risk level.
- Tests, benchmarks, or manual checks needed.
- Clear statement that no files were modified, unless explicitly requested.

Only edit files when asked to implement, fix, optimize, apply, change, or refactor. Analysis-only requests produce no file modifications.

## Workflow

1. **Baseline**: Identify language, framework, test/build commands, hot paths. Inspect existing tests. Run the bundled scanner for a first-pass hotspot list:
   ```bash
   python3 ~/.claude/commands/complexity-optimizer/analyze_complexity.py /path/to/repo --format markdown
   ```

2. **Rank**: Prioritize hot paths, large-input paths, rendering loops, DB/API loops, shared utilities. Separate algorithmic complexity from constant-factor cleanup. Scanner output = leads, not proof.

3. **Prove behavior**: Locate or add focused tests. Cover edge cases (empty input, duplicates, ordering stability, nulls, errors, permissions, pagination, mutations). If tests are absent and behavior is ambiguous, ask before changing semantics.

4. **Optimize conservatively**:
   - Linear lookups → maps/sets when key equality is stable.
   - Nested scans → indexing, grouping, two-pointer, sweep-line, binary search, memoization, batching.
   - UI: reduce re-renders with stable props, memoized derived data, virtualization.
   - Data access: remove N+1 with bulk fetches, joins, preloading, caching, batching.
   - Before applying changes, snapshot the original function for benchmark comparison in Step 6.

5. **Verify**: Run tests + type/lint/build. Add micro-benchmarks when improvement is non-obvious. Report original vs new complexity, changed files, tests run, residual risk.

6. **Benchmark** (post-implementation only):
   - Skip if user only requested analysis/report.
   - Generate temporary benchmark script (`/tmp/bench_<name>.<ext>`) measuring original vs optimized.
   - Data: project fixtures first (`tests/`, `fixtures/`, `__tests__/`, `test_data/`), synthetic fallback (1,000+ elements).
   - Python: `timeit.repeat()` min of 5×1000 for speed, `tracemalloc` peak for RAM.
   - JS/TS: `performance.now()` avg of 1000 for speed, `process.memoryUsage().heapUsed` delta for RAM.
   - Delete temp scripts after capture. If benchmark fails, report reason and fall back to theoretical estimates.

7. **Performance report**: Add `## Performance Benchmark` section with table: Function | Metric | Before | After | Delta | Change%. Auto-scale units (μs/ms/s, KB/MB/GB). Include data source, iterations, runtime version, and dev-machine disclaimer.

## Safety Checklist

Before editing:
- Data sizes large enough for complexity to matter?
- Output ordering preserved?
- Object identity/mutability not part of public behavior?
- Caches have invalidation strategy?
- Dedup doesn't collapse distinct records sharing a display label?
- DB batching preserves tenant/permission/soft-delete/pagination/sorting constraints?

After editing:
- Run narrow test first, then broadest relevant suite.
- Compare before/after benchmark numbers.
- Keep patch localized, no formatting churn.

## References

The bundled `optimization-playbook.md` covers common transformations:
- Nested lookup loops → map index (O(a*b) → O(a+b))
- Repeated membership → Set (O(n*m) → O(n+m))
- Sort in loops → sort once / heap (O(n^2 log n) → O(n log n))
- Pairwise comparisons → sort+two-pointer / sweep-line (O(n^2) → O(n log n))
- Render-path recomputation → memoized selectors / virtualization
- N+1 queries → bulk fetch / joins / dataloaders
