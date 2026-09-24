# C# / .NET

## Algorithms and collections

- **`list.Contains(x)` / `IndexOf` / LINQ `FirstOrDefault(pred)` inside a loop:** O(n*m). Build a `HashSet<T>` or `Dictionary<K, V>` (`ToDictionary`, `ToLookup`) once. *membership-in-loop, nested-loop*
- **`string s += piece` in a loop:** use `StringBuilder` or `string.Join`. *string-concat-in-loop*
- **`list.RemoveAt(0)` / `Insert(0, x)` in a loop:** use `Queue<T>` / `LinkedList<T>`. *list-shift-in-loop*
- **`new Regex(...)` per call:** make it `static readonly` with `RegexOptions.Compiled`, or use `[GeneratedRegex]` (.NET 7+). *regex-compile-in-loop*
- **Enumerating an `IEnumerable` query several times:** each enumeration re-runs the query (or the DB call); materialize once with `ToList()` when reused.
- **`Count()` on an `IEnumerable` to check emptiness:** use `Any()`, or `Count` on lists.
- **Allocations in hot paths:** `Span<T>`, `ArrayPool<T>`, and `stackalloc` avoid them when profiling shows GC pressure.

## Entity Framework Core

- **Lazy loading or queries per element in loops:** `Include` / `ThenInclude`, or one query with `Where(x => ids.Contains(x.Id))`.
- **Tracking entities you only read:** `AsNoTracking()`.
- **Loading full entities for a few fields:** project with `Select(x => new { ... })`.
- **`SaveChanges()` per entity in a loop:** add all, then one `SaveChanges()`; for large sets use `ExecuteUpdate` / `ExecuteDelete` (EF Core 7+) or bulk libraries.
- **Client-side evaluation of filters:** make sure the `Where` translates to SQL; check with `ToQueryString()` or `LogTo(Console.WriteLine)`.

## Async

- **`await` per element for independent calls:** `await Task.WhenAll(items.Select(...))`, limited with `Parallel.ForEachAsync` (`MaxDegreeOfParallelism`) or `SemaphoreSlim`. *await-in-loop*
- **`.Result` / `.Wait()` on tasks:** blocks threads and can deadlock; await instead.

## Measure

BenchmarkDotNet with `[MemoryDiagnoser]` for micro-benchmarks, `dotnet-trace` and `dotnet-counters` for running apps. Details in `../measuring.md`.
