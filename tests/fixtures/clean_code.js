function lookupAll(keys, cache) {
  const results = [];
  for (const key of keys) {
    results.push(cache.get(key));
  }
  return results;
}

function evict(ids, pending) {
  for (const id of ids) {
    pending.delete(id);
  }
}
