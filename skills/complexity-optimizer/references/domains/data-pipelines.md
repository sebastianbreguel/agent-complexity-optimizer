# Data Pipelines (ETL, batch jobs, notebooks)

Pipelines are slow for three reasons: they move more data than needed, they process it row by row in Python/JS instead of in a vectorized engine, or they wait on I/O one call at a time. Time each stage before changing anything.

## Move less data

- **Read only what you need:** columns (`usecols`, `columns=` in Parquet readers, `SELECT a, b`), rows (push filters into the query or use predicate pushdown in Parquet/Polars/Spark), and partitions (date-partitioned paths).
- **Columnar formats:** Parquet instead of CSV/JSON for anything read more than once; it's smaller and typed.
- **Incremental loads:** process only new or changed rows (watermark column, CDC, i.e. change data capture) instead of full reloads every run.
- **Avoid `collect()` / `toPandas()` on big Spark data:** it pulls everything to the driver; aggregate first.

## Vectorize instead of looping

- **pandas:** replace `iterrows` / `apply(axis=1)` with column operations, `merge`, `groupby().agg()`, `np.where`. *dataframe-row-loop*
- **Building frames in a loop** (`pd.concat` / `append` per chunk): collect the pieces in a list and concatenate once. *quadratic-accumulation*
- **Polars:** use the lazy API (`scan_parquet(...).filter(...).group_by(...).collect()`) so the optimizer can push down filters and projections.
- **Spark:** prefer built-in functions over Python UDFs (UDFs serialize every row to Python); use broadcast joins for small dimension tables; fix skewed keys (one partition doing all the work) by salting; `explain()` the plan; cache only DataFrames reused several times.
- **Dtypes:** `category` for repeated strings, smaller numeric types when ranges allow; check with `df.info(memory_usage="deep")`.

## I/O and external calls

- **One API/DB call per row:** batch requests or bulk endpoints; with concurrency limits and retries with backoff when the API allows parallel calls. *io-or-query-in-loop, await-in-loop*
- **Loading into the warehouse row by row:** use bulk loaders (`COPY`, `executemany`, BigQuery load jobs, Snowflake `COPY INTO`).
- **Many small files** (thousands of tiny Parquet/CSV files): compact them; per-file overhead dominates.
- **Re-running expensive steps:** cache intermediate results (Parquet checkpoints) keyed by input version, so a failure late in the pipeline doesn't redo the early stages.

## LLM and embedding pipelines

- **One model call per item when the API supports batches:** use the batch or embeddings endpoints with many inputs per request.
- **Sequential calls:** bounded concurrency (`asyncio.Semaphore`, `p-limit`) within the provider's rate limits.
- **Re-embedding unchanged text:** cache by content hash.

## Measure

Time per stage and rows per second (log both), peak memory (`/usr/bin/time -l` / `-v`, `memray` for Python), `%timeit` in notebooks, `line_profiler` for line-level hot spots, the Spark UI for stage times and skew. See `../measuring.md`.
