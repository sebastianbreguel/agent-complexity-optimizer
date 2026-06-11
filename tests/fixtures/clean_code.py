def sum_values(items):
    return sum(item["value"] for item in items)


def build_index(records):
    return {r["id"]: r for r in records}


def lookup_all(keys, mapping):
    results = []
    for key in keys:
        results.append(mapping.get(key))
    return results


def filter_known(items, known_ids):
    known = set(known_ids)
    return [item for item in items if item["id"] in known]


def keep_valid(rows):
    valid = []
    for row in rows:
        if row["status"] in ("active", "pending"):
            valid.append(row)
    return valid
