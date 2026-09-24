# JavaScript / TypeScript (Node and shared code)

For React components see `react.md`. Each item: pattern, cost, better version, and the scanner pattern (or what to search for).

## Algorithms and data structures

- **`array.includes / indexOf / find / some` inside a loop or callback:** O(n*m). Build a `Set` (membership) or a `Map` keyed by id (lookup) once. *membership-in-loop, nested-loop*
- **`reduce` that spreads the accumulator** (`(acc, x) => ({ ...acc, [x.id]: x })` or `[...acc, x]`): copies on every element, O(n^2). Mutate the accumulator (`acc[x.id] = x; return acc`), or use `Object.fromEntries(items.map(...))` / `new Map(...)`. *quadratic-accumulation*
- **`all = all.concat(page)` in a loop:** use `all.push(...page)` (small pages) or collect pages and `.flat()` once. *quadratic-accumulation*
- **`array.shift()` / `unshift()` / `splice(0, 1)` in a loop:** re-indexes the array each time. Iterate by index, reverse once and `pop()`, or use a real queue. *list-shift-in-loop*
- **Sorting inside a loop or on every call of a hot function:** sort once and cache, or keep a sorted structure. *sort-in-loop*
- **`JSON.parse(JSON.stringify(x))` / `structuredClone` / `cloneDeep` per item:** copy once, or update immutably only the changed path. *deep-copy-in-loop*
- **`new RegExp(...)` in a loop:** compile once outside. *regex-compile-in-loop*
- **Chains like `.filter().map().filter()` on large arrays in hot paths:** each link allocates a new array; merge them into one loop or one `reduce` when profiling shows it matters.
- **`Object.keys(obj).length` / `Object.entries` inside loops over the same object:** compute once.
- **`array.length` in a `for` header:** not a problem in modern engines; don't "optimize" it.

## I/O, databases and async

- **`await` inside `for...of` for independent calls:** requests run one at a time. Use `Promise.all(items.map(...))`, with a concurrency limit for large lists (`p-limit`, or chunks + `Promise.all`). Keep sequential when order, transactions, or rate limits require it. *await-in-loop* (ESLint's `no-await-in-loop` rule flags the same thing.)
- **`items.forEach(async (x) => { await ... })`:** the awaits are not awaited by the caller; errors and completion are lost. Use `for...of` (sequential) or `Promise.all` (parallel).
- **Repository/ORM call per element** (`await repo.findOne(...)` in a loop): one query with `In([...ids])` / `where: { id: { in: ids } }`, then index the result in a `Map`. *io-or-query-in-loop*
- **TypeORM/Prisma relations loaded lazily in loops:** load them with `relations` / `include` in the original query; turn on query logging (`logging: true`, Prisma `log: ["query"]`) to count queries.
- **Row-by-row `save()` in a loop:** `save(entities)` with an array, `insertMany` / `createMany`, or a single `UPDATE ... WHERE id IN`.
- **Sync APIs on the request path** (`fs.readFileSync`, `crypto.pbkdf2Sync`, large `JSON.parse` of big payloads): they block the event loop for every request. Use async versions, streams, or a worker thread.
- **Unbounded in-memory caches** (`const cache = {}` that only grows): memory leak under load. Use an LRU with a max size and TTL.

## TypeScript build and tooling

- **Slow type-checking:** `tsc --extendedDiagnostics` shows time per phase; `tsc --generateTrace trace` shows the expensive types. Deep conditional/recursive types and huge unions are usual causes.
- **Barrel files (`index.ts` re-exporting everything)** slow bundlers and tests by importing whole modules; import from the specific file on hot paths.

## Measure

`node --cpu-prof app.js` (open the `.cpuprofile` in Chrome DevTools), `clinic flame -- node app.js`, `vitest bench` or `tinybench` for micro-benchmarks, `hyperfine` for whole commands. Details in `../measuring.md`.
