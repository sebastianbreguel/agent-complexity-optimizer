# Data Access (SQL and ORMs)

Most backend latency is database time: too many queries, or queries that scan too many rows. Count queries first, then read plans.

## Too many queries

- **N+1:** one query for a list, then one per item (explicit calls in a loop, or lazy relations touched in a loop, serializer, or template). Fix with one query for all ids (`WHERE id = ANY($1)` / `IN (...)`) or eager loading, then join in memory with a map. ORM names: Django `select_related` / `prefetch_related`, SQLAlchemy `selectinload` / `joinedload`, Rails `includes`, JPA `JOIN FETCH` / `@EntityGraph`, EF Core `Include`, TypeORM `relations`, Prisma `include`. *io-or-query-in-loop* catches explicit calls; lazy relations need reading the loop body.
- **Writes per row:** batch them: multi-row `INSERT ... VALUES (...), (...)`, `executemany`, `bulk_create` / `insert_all` / `createMany` / `saveAll` with JDBC batching, `UPDATE ... FROM (VALUES ...)`, or `COPY` for large loads.
- **One transaction per row:** commit per batch instead; per-row commits force a disk flush each time.
- **Counting queries:** turn on query logging in development (Django debug toolbar or `assertNumQueries`, SQLAlchemy `echo=True`, Rails log / `bullet`, Hibernate statistics, TypeORM `logging: true`, Prisma `log: ["query"]`, EF Core `LogTo`). A request that runs hundreds of queries is the finding, even when each one is fast.

## Queries that scan too much

- **Missing index on filtered, joined, or sorted columns** (foreign keys are the usual gap): `EXPLAIN (ANALYZE, BUFFERS)` shows `Seq Scan` with large `rows`. Add the index that matches the filter + sort order (composite indexes are used left to right).
- **Functions on indexed columns** (`WHERE lower(email) = ...`, `WHERE date(created_at) = ...`): the index can't be used; add an expression index or rewrite as a range (`created_at >= day AND created_at < day + 1`).
- **`OFFSET` pagination on large tables:** the database still reads and discards the skipped rows; use keyset pagination (`WHERE (created_at, id) < ($1, $2) ORDER BY created_at DESC, id DESC LIMIT 50`).
- **`SELECT *` on wide tables** (JSON/text columns): select only the needed columns.
- **`COUNT(*)` on big tables for UI badges:** cache it, use estimates (`pg_class.reltuples`), or cap it (`LIMIT 1001`).
- **Huge `IN (...)` lists:** pass an array (`= ANY($1)`) or join against a temporary table / `VALUES` list.
- **Leading-wildcard `LIKE '%term%'`:** can't use a B-tree index; use trigram indexes (`pg_trgm`) or full-text search.
- **Sorting or grouping large result sets in application code** that the database could do with an index.

## Connections and caching

- **No connection pooling, or a pool smaller than concurrency:** requests queue for a connection; it looks like slow queries.
- **Caching without invalidation:** stale data bugs. Cache only with a clear key, TTL, and invalidation path.

## Measure

`EXPLAIN (ANALYZE, BUFFERS)` before and after (PostgreSQL), `pg_stat_statements` ordered by `total_exec_time` to find the queries that cost the most overall, and query counts per request from the ORM logs. See `../measuring.md`.
