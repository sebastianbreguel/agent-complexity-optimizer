# JVM (Java, Kotlin, Scala)

## Algorithms and collections

- **`list.contains(x)` / `indexOf` inside a loop:** O(n*m) on `ArrayList`. Use a `HashSet` / `HashMap` built once. *membership-in-loop*
- **`String s += piece` in a loop:** each append copies the string, O(n^2). Use `StringBuilder` (Java, Kotlin `buildString { }`) or `String.join` / `joinToString`. *string-concat-in-loop*
- **`list.remove(0)` / `list.add(0, x)` on `ArrayList` in a loop:** shifts every element. Use `ArrayDeque`. *list-shift-in-loop*
- **`Pattern.compile` per call:** compile once into a `static final` field (Kotlin: top-level `val` or companion object). *regex-compile-in-loop*
- **Nested loops or stream-inside-stream to join collections:** group one side with `Collectors.groupingBy` / Kotlin `associateBy` / `groupBy`, then look up. *nested-loop*
- **Boxing in hot numeric loops** (`List<Integer>`, `Map<Long, ...>`): use primitive arrays or specialized collections when profiling shows allocation pressure.
- **Kotlin: chaining many operators on large lists** (`filter`, `map`, `filter`): each allocates a list; use `asSequence()` for long chains on big collections.
- **Exceptions for control flow in loops:** creating exceptions (stack traces) is expensive; check conditions first.

## Data access (JPA / Hibernate / Spring Data)

- **Lazy associations accessed in loops or serializers:** classic N+1. Use `JOIN FETCH`, `@EntityGraph`, or batch fetching (`hibernate.default_batch_fetch_size`). Enable SQL logging or Hibernate statistics to count queries.
- **`repository.save()` per entity:** `saveAll` plus JDBC batching (`hibernate.jdbc.batch_size`, `order_inserts=true`).
- **Loading entities just to read one field:** use projections / DTO queries.
- **Missing pagination on large result sets:** stream (`Stream<T>` with a read-only transaction) or paginate with keyset queries.

## Concurrency

- **Blocking calls on reactive or coroutine threads** (WebFlux, Kotlin coroutines on `Dispatchers.Default`): move them to `Dispatchers.IO` / `boundedElastic`.
- **Sequential independent remote calls:** `CompletableFuture.allOf`, Kotlin `coroutineScope { ids.map { async { ... } }.awaitAll() }` with a limit (`Semaphore`).

## Measure

async-profiler (`asprof -d 30 -f flame.html <pid>`), JDK Flight Recorder + Mission Control, JMH for micro-benchmarks (never time with `System.currentTimeMillis` loops: the JIT distorts them). Details in `../measuring.md`.
