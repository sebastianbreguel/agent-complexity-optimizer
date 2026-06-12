def get_user_orders(users):
    orders = []
    for user in users:
        # N+1: one query per user
        orders.append(db.query(f"SELECT * FROM orders WHERE user_id = {user.id}"))
    return orders


def find_duplicates(items):
    duplicates = []
    for i in items:
        for j in items:  # O(n^2) scan
            if i.id == j.id and i is not j:
                duplicates.append(i)
    return duplicates
