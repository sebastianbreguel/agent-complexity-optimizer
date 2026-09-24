# Optimization Playbook

## Common Transformations

### Nested lookup loops

Symptom: for each item in A, scan all of B to find a match.

Preferred fix: build a map from B once, then perform O(1) lookups.

Complexity: O(a*b) to O(a+b).

Correctness checks:

- Are duplicate keys possible?
- Does the original code pick first match, last match, or all matches?
- Is ordering observable?
- Is key normalization required?

### Repeated membership checks

Symptom: `items.includes(x)`, `x in list`, `array.indexOf(x)`, or equivalent inside a loop.

Preferred fix: convert the membership collection to a set once.

Complexity: O(n*m) to O(n+m).

Correctness checks:

- Does equality change after conversion? JavaScript object identity and Python hashability matter.
- Are values normalized the same way?

### Sorting inside loops

Symptom: sorting the same or growing collection repeatedly.

Preferred fix: sort once outside the loop, maintain a heap, or use binary insertion/search.

Complexity: often O(n^2 log n) to O(n log n), or O(n log k) with a heap.

Correctness checks:

- Is each intermediate sorted state externally observed?
- Does the comparator depend on loop-local state?

### Pairwise comparisons

Symptom: compare every pair to find overlaps, nearest values, conflicts, or ranges.

Preferred fixes:

- Sort + two pointers for pair/range matching.
- Sweep line for interval overlaps.
- Spatial/hash bucketing for local-neighborhood checks.
- Union-find for connectivity.

Complexity: commonly O(n^2) to O(n log n) or O(n alpha(n)).

### Recomputing derived data in render paths

Symptom: filters, sorts, grouping, or expensive transforms run during every render.

Preferred fixes:

- Memoize derived values with correct dependencies.
- Move derivation to selectors, loaders, or server-side preparation.
- Virtualize long lists.
- Stabilize callbacks and object props only when child renders are measurably affected.

Correctness checks:

- Dependency arrays must include every semantic input.
- Memoization must not hide mutations of mutable input objects.

### N+1 database or API calls

Symptom: a query or request inside a loop.

Preferred fixes:

- Bulk fetch by IDs and join in memory.
- Use joins, includes/preloads, dataloaders, or batched API endpoints.
- Preserve filtering, authorization, tenancy, ordering, pagination, and error behavior.

Correctness checks:

- Do not fetch records the previous per-item logic would not authorize.
- Preserve missing-record behavior.
- Preserve rate-limit and retry semantics.

### Sequential awaits in a loop

Symptom: `for (const x of items) { await call(x) }` where the calls don't depend on each other.

Preferred fix: start them together with a concurrency limit: `Promise.all` over chunks or `p-limit` (JS), `asyncio.gather` with a `Semaphore` or `TaskGroup` (Python), `errgroup` with `SetLimit` (Go), `Task.WhenAll` / `Parallel.ForEachAsync` (C#).

Complexity: total latency goes from sum(call times) to about max(call time) per wave; the work is the same.

Correctness checks:

- Does a later call depend on an earlier result, or on its side effects (ordering, transactions, idempotency)?
- Will parallel calls hit rate limits, connection pool limits, or lock contention?
- Is partial failure handled (all-or-nothing vs `allSettled`)?

### Collections rebuilt on every iteration

Symptom: `acc = [...acc, x]`, `{ ...acc, [k]: v }` in `reduce`, `all = all.concat(page)`, `df = pd.concat([df, row])`, `s += piece` on immutable strings (Java, C#, Go, Kotlin).

Preferred fix: mutate one accumulator (`push`, `append`, `acc[k] = v`, `StringBuilder`, `strings.Builder`), or collect the parts and combine once after the loop.

Complexity: O(n^2) to O(n).

Correctness checks:

- Is the accumulator shared or exposed while the loop runs (immutability relied on elsewhere)?
- Is the original input mutated by the new version?

### Front removal from array lists

Symptom: `pop(0)`, `shift()`, `remove(0)`, `insert(0, x)` inside a loop.

Preferred fix: a deque (`collections.deque`, `ArrayDeque`, `VecDeque`), or iterate by index.

Complexity: O(n^2) to O(n).

### Per-iteration setup work

Symptom: compiling a regex, building a formatter, deep-copying a template, or parsing the same config inside a loop or per request.

Preferred fix: hoist it out of the loop or to module/static scope; copy only what changes.

Complexity: removes a constant (sometimes large) per iteration; matters in hot paths.

### Row-by-row DataFrame work

Symptom: `iterrows()`, `itertuples()`, `apply(axis=1)`, Python loops over DataFrame rows.

Preferred fix: vectorized column expressions, `merge`, `groupby().agg()` / `transform()`, `np.where` / `np.select`.

Complexity: same big-O, but typically 10-100x faster because the work runs in compiled code.

Correctness checks:

- Missing values (`NaN`) propagate differently in vectorized expressions than in Python `if` checks.
- Integer columns with missing values become floats; check dtypes of the result.

## What Not To Do

- Do not replace clear linear code with complex structures when input sizes are tiny or the path is cold.
- Do not cache without invalidation.
- Do not use JSON serialization as a general-purpose key unless the key format is stable and collision-safe for the domain.
- Do not change public ordering unless tests and callers prove it is irrelevant.
- Do not trade O(n) for O(n log n) unless it removes a larger bottleneck or enables batching.
- Do not parallelize calls without a concurrency limit; unbounded fan-out moves the bottleneck to the database or the API's rate limit.
- Do not claim a speedup without a measurement; say "estimated" when there is none.
