# Rust

Always measure with `--release`; debug builds can be 10-100x slower and mislead every comparison.

## Algorithms and allocations

- **`vec.contains(&x)` / `iter().position` inside a loop:** O(n*m). Use a `HashSet` / `HashMap` built once. *membership-in-loop*
- **Nested loops to match two collections:** index one side in a `HashMap` keyed by the join field. *nested-loop*
- **`vec.remove(0)` / `insert(0, x)` in a loop:** shifts every element; use `VecDeque`. *list-shift-in-loop*
- **`Regex::new` in a function called per item:** compile once with `std::sync::LazyLock` (1.80+) or `once_cell::sync::Lazy`. *regex-compile-in-loop*
- **`.clone()` of large values inside loops to satisfy the borrow checker:** borrow (`&T`), use `Rc`/`Arc` for shared ownership, or restructure the loop.
- **`.collect::<Vec<_>>()` only to iterate again:** chain the iterators instead.
- **Growing `Vec` / `String` without capacity** when the size is known: `Vec::with_capacity(n)`, `String::with_capacity(n)`.
- **`format!` / `to_string()` in hot loops:** allocates each time; write into a reused buffer with `write!`.
- **Default `HashMap` hasher (SipHash) in hot, trusted-input paths:** a faster hasher (`rustc-hash` / `ahash`) helps when profiling shows hashing cost. Keep SipHash for untrusted keys (it resists HashDoS attacks).

## I/O and async

- **Unbuffered file or socket I/O** (`File::read` / `write` in small chunks): wrap in `BufReader` / `BufWriter`.
- **`.await` per element for independent futures:** `futures::future::join_all`, or `stream::iter(...).buffer_unordered(n)` for a concurrency limit. *await-in-loop*
- **Blocking calls inside async tasks** (`std::fs`, heavy CPU): `tokio::task::spawn_blocking` or async equivalents.
- **Holding a `Mutex` guard across `.await`:** serializes tasks and can deadlock with `std::sync::Mutex`; drop the guard first or use `tokio::sync::Mutex`.

## Measure

`criterion` benchmarks with `cargo bench`, `cargo flamegraph` or `samply record` for profiles. Details in `../measuring.md`.
