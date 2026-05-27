def sum_values(items):
    return sum(item["value"] for item in items)


def build_index(records):
    return {r["id"]: r for r in records}
