function findDuplicates(listA, listB) {
  const results = [];
  for (const a of listA) {
    for (const b of listB) {
      if (a.id === b.refId) {
        results.push({ a, b });
      }
    }
  }
  return results;
}
