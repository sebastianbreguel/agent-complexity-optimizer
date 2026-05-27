def remove_banned(items, banned_names):
    clean = []
    for item in items:
        if item["name"] not in banned_names:
            clean.append(item)
    return clean
