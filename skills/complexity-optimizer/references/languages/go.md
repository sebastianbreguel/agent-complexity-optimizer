# Go

## Algorithms and allocations

- **Nested loops to match slices:** build a `map[K]V` (or `map[K]struct{}` as a set) once, then look up. *nested-loop, membership-in-loop*
- **`s += piece` building strings in a loop:** strings are immutable, so each append copies, O(n^2). Use `strings.Builder` (and `b.Grow(n)` when the size is known). *string-concat-in-loop*
- **`append` into a slice whose final size is known:** preallocate with `make([]T, 0, n)` to avoid repeated growth copies.
- **`regexp.MustCompile` inside a function called per request or per item:** compile once at package level. *regex-compile-in-loop*
- **Sorting inside a loop:** sort once (`slices.Sort`, `sort.Slice`), or use `container/heap` for top-k. *sort-in-loop*
- **Removing from the front** (`s = append(s[:0], s[1:]...)` per element): use an index or a ring buffer.
- **`defer` inside a long loop:** runs only when the function returns, so resources pile up. Close explicitly in the loop body or move the body into a function.
- **Converting `[]byte` <-> `string` repeatedly in hot paths:** each conversion copies; keep one representation.
- **Values escaping to the heap unnecessarily:** `go build -gcflags=-m` shows what escapes; returning pointers to small structs or capturing loop variables in closures can force allocations.

## I/O, databases and concurrency

- **`db.Query` / HTTP call per element:** one query with `WHERE id = ANY($1)` (pgx) or `IN (...)`, then index in a map. *io-or-query-in-loop*
- **Sequential independent calls:** run them with `errgroup.Group` and `g.SetLimit(n)`; don't spawn one goroutine per item without a limit.
- **Forgetting `rows.Close()` / `resp.Body.Close()`:** leaks connections until the pool is exhausted, which looks like slowness.
- **Unbuffered channels between fast producers and slow consumers:** everything moves at the speed of the slowest step; add buffering or more workers where the profile shows blocking.
- **A mutex held during I/O:** serializes all goroutines; hold locks only around the shared state.

## Measure

`go test -bench=. -benchmem -cpuprofile cpu.out` then `go tool pprof -top cpu.out`; `benchstat old.txt new.txt` to compare runs; `net/http/pprof` for live services; `go test -race` before shipping concurrency changes. Details in `../measuring.md`.
