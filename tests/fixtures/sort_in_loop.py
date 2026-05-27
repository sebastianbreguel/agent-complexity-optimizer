def sorted_batches(records, batch_size):
    results = []
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch.sort(key=lambda x: x["score"])
        results.extend(batch)
    return results
