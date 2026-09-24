import asyncio


def n_plus_one(user_ids, db):
    for uid in user_ids:
        db.query(f"SELECT * FROM users WHERE id = {uid}")  # expect: io-or-query-in-loop


def django_orm(ids, User):
    for i in ids:
        User.objects.get(id=i)  # expect: io-or-query-in-loop


def http_calls(urls, requests):
    return [requests.get(url) for url in urls]  # expect: io-or-query-in-loop


def not_a_database(learner, n):
    for _ in range(n):
        learner.query(num_samples=20)


def dict_get(keys, mapping):
    for key in keys:
        mapping.get(key)


def raw_sql(ids, cursor):
    for i in ids:
        cursor.execute("SELECT 1 WHERE id = %s", (i,))  # expect: io-or-query-in-loop


async def sequential_client(urls, client):
    for url in urls:
        await client.get(url)  # expect: io-or-query-in-loop


async def notify_each(jobs):
    for job in jobs:
        await process(job)  # expect: await-in-loop


async def run_sequential(jobs):
    for job in jobs:
        await process(job)


async def first_match(jobs):
    for job in jobs:
        if job.ready:
            return await process(job)


async def retry(job, max_retries):
    for attempt in range(max_retries):
        result = await process(job)
        if result:
            return result


async def gathered(jobs):
    await asyncio.gather(*(process(j) for j in jobs))


async def rate_limited(jobs):
    for job in jobs:
        await asyncio.sleep(1)


async def paginate(client):
    cursor = None
    while True:
        page = await client.get("/items", params={"cursor": cursor})
        cursor = page.next
        if cursor is None:
            break


async def in_batches(chunks, db):
    for chunk in chunks:
        await db.insert(chunk)


async def process(job):
    return job


def chunked_ids(ids, conn, size):
    rows = []
    for i in range(0, len(ids), size):
        chunk = ids[i : i + size]
        rows.extend(conn.execute("SELECT * FROM t WHERE id = ANY(:ids)", {"ids": chunk}).all())
    return rows


def stepped_batches(ids, db, batch_size):
    for start in range(0, len(ids), batch_size):
        db.query("SELECT 1", ids[start : start + batch_size])


def rows_of_a_batch(batch, db):
    for row in batch:
        db.save(row)  # expect: io-or-query-in-loop


def rows_inside_chunks(chunks, db):
    for chunk in chunks:
        for row in chunk:
            db.save(row)  # expect: io-or-query-in-loop


def links_of_a_webpage(webpage, requests):
    for link in webpage.links:
        requests.get(link)  # expect: io-or-query-in-loop


def retry_inside_for(urls, requests):
    for url in urls:
        attempts = 0
        while attempts < 3:
            requests.get(url)  # expect: io-or-query-in-loop
            attempts += 1


async def serialize_orders(orders):
    for order in orders:
        await enrich(order)  # expect: await-in-loop


def flask_sqlalchemy(ids, User):
    for uid in ids:
        User.query.filter_by(id=uid).first()  # expect: io-or-query-in-loop
        User.query.get(uid)  # expect: io-or-query-in-loop


async def enrich(order):
    return order
