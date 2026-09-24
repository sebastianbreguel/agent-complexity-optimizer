# Python

Each item: the inefficient pattern, why it costs, the better version, and the scanner pattern that flags it (or what to search for when the scanner can't).

## Algorithms and data structures

- **`x in some_list` / `list.index(x)` / `list.count(x)` / `list.remove(x)` in a loop:** each call scans the list, O(n*m) total. Build `set(...)` or `dict` once before the loop; use `collections.Counter` for counts. *membership-in-loop*
- **`list.pop(0)` / `list.insert(0, x)` in a loop:** shifts every element, O(n^2). Use `collections.deque` (`popleft`, `appendleft`). *list-shift-in-loop*
- **`out = out + [x]`, `d = {**d, k: v}`, `s = s | {x}` in a loop:** copies the whole collection each iteration. Use `append` / `extend`, `d[k] = v`, `s.add(x)`. *quadratic-accumulation*
- **Sorting inside a loop** (`sorted(...)` on a growing list): sort once after the loop, use `heapq` for top-k, or `bisect.insort` to keep order incrementally. *sort-in-loop*
- **Nested loops to match two collections:** index one side in a dict keyed by the join field, then do one pass. *nested-loop*
- **`copy.deepcopy` per item:** copy once, or copy only the fields that change. *deep-copy-in-loop*
- **Recomputing the same value in a loop** (a `len()` of an unchanged list is fine; a regex compile, a DB lookup, or a parse of the same config is not): hoist it out, or cache with `functools.cache` when inputs are hashable and results don't go stale.
- **String building with `+=` in a hot loop:** CPython often optimizes it, but not reliably (for example when another reference exists); prefer `"".join(parts)`.
- **Exponential recursion** (naive Fibonacci-style recurrences, backtracking without pruning): memoize with `functools.cache` or convert to dynamic programming. Search for recursive functions called twice per level.

## I/O, databases and async

- **Query or HTTP call per element** (`for id in ids: db.get(id)`, `requests.get` per URL): fetch in bulk (`WHERE id IN (...)`, `filter(id__in=...)`), or use the API's batch endpoint. *io-or-query-in-loop*
- **Django lazy relations in loops or templates** (`for order in orders: order.customer.name`): `select_related` (FK, one-to-one) or `prefetch_related` (many-to-many, reverse FK). Verify with `assertNumQueries` or django-debug-toolbar.
- **SQLAlchemy lazy loading:** `selectinload` / `joinedload` in the query; `raiseload("*")` in tests to catch accidental lazy loads.
- **`await` per element in a `for` loop:** independent calls run one after another. Use `asyncio.gather` with a limit (`asyncio.Semaphore`), or `asyncio.TaskGroup` (3.11+). *await-in-loop*
- **Blocking calls inside `async def`** (`requests`, `time.sleep`, heavy CPU, sync DB drivers): they stall the event loop for every request. Use async clients (`httpx.AsyncClient`, `asyncpg`), `asyncio.sleep`, or `asyncio.to_thread` for unavoidable blocking work. Search `async def` bodies for `requests.`, `time.sleep`, `open(`.
- **Row-by-row inserts/updates:** use `executemany`, `bulk_create` / `bulk_update`, `insert().values([...])`, or `COPY` for large loads.
- **Reading a whole file or result set into memory** when streaming works: iterate the file object, use server-side cursors or `yield_per`.

## Data (pandas / NumPy)

- **`df.iterrows()`, `itertuples()`, `df.apply(f, axis=1)`:** Python-level work per row. Use vectorized column operations, `np.where` / `np.select`, `merge`, `groupby().agg()` / `transform()`. *dataframe-row-loop*
- **`df = pd.concat([df, row])` or `np.append` in a loop:** copies everything each time. Collect rows in a list and build the frame once. *quadratic-accumulation*
- **Growing a frame with `df.loc[len(df)] = row`:** same problem; collect then construct.
- **Wrong dtypes:** object columns of repeated strings use far more memory than `category`; check with `df.info(memory_usage="deep")`. Read only needed columns: `read_csv(usecols=..., dtype=...)`, or use Parquet.
- **Chained filtering copies** (`df[df.a > 0][df.b < 5]`): combine masks in one `.loc[mask]`.
- **`groupby().apply` with Python functions:** prefer built-in aggregations; they run in C.

## Measure

`py-spy record -o profile.svg -- python app.py` for where the time goes, `python -m timeit` or `timeit.repeat()` for micro-benchmarks, `pytest --durations=15` for slow tests, `line_profiler` (`kernprof -l -v script.py`) for line-level cost, `memray` for memory. Details in `../measuring.md`.
