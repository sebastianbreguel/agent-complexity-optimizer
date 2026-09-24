# Ruby / Rails

## Algorithms and collections

- **`array.include?(x)` inside `each` / `select`:** O(n*m). Convert once with `to_set` (or build a hash with `index_by` / `group_by`). *membership-in-loop*
- **Nested `each` to match two collections:** `index_by(&:id)` one side, then look up. *nested-loop*
- **`str += piece` in loops:** creates a new string each time; use `<<` on a mutable string or `Array#join`.
- **`array.shift` in a loop over a large array:** iterate with `each` instead, or use an index.
- **Building hashes with `merge` in `inject`/`reduce`** (`inject({}) { |h, x| h.merge(x.id => x) }`): copies the hash each step; use `each_with_object({})` or `index_by`. *quadratic-accumulation*

## ActiveRecord

- **Associations accessed in loops or views** (`@posts.each { |p| p.author.name }`): N+1 through lazy loading, invisible to the scanner (it looks like attribute access). Use `includes` (or `preload` / `eager_load`). Catch them with the `bullet` gem or `strict_loading` (Rails 6.1+).
- **`find` / `find_by` per id in a loop:** `where(id: ids)` once, then `index_by(&:id)`. *io-or-query-in-loop*
- **`.count` on loaded associations in loops:** use `size` (uses the loaded records) or counter caches.
- **`each` over huge tables:** `find_each` / `in_batches` to avoid loading everything.
- **Callbacks and validations on bulk writes:** `insert_all` / `upsert_all` / `update_all` skip them; use them for backfills when that's acceptable.
- **Missing indexes on foreign keys and filtered columns:** check with `EXPLAIN` (`relation.explain`).

## Measure

`rack-mini-profiler` (with flamegraphs) in development, `stackprof` / `rbspy` for CPU, `benchmark-ips` for micro-benchmarks. Details in `../measuring.md`.
