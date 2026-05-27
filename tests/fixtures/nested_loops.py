def find_matches(list_a, list_b):
    results = []
    for a in list_a:
        for b in list_b:
            if a["id"] == b["ref_id"]:
                results.append((a, b))
    return results
