def cross_product(users, orders):
    for u in users:
        for o in orders:  # expect: nested-loop
            if o.user_id == u.id:
                yield u, o


def walk_rows(rows):
    total = 0
    for row in rows:
        for cell in row:
            total += cell
    return total


def walk_items(orders):
    for order in orders:
        for line in order.lines:
            print(line)


def pairwise(points):
    for i in range(len(points)):
        for j in range(i + 1, len(points)):  # expect: nested-loop
            compare(points[i], points[j])


def retries(items):
    for attempt in range(3):
        for item in items:
            send(item, attempt)


def flatten(groups, tags):
    return [(g, t) for g in groups for t in tags]  # expect: nested-loop


def triple(a, b, c):
    for x in a:
        for y in b:  # expect: nested-loop
            for z in c:  # expect: nested-loop
                print(x, y, z)


def closure_defined_in_loop(items):
    handlers = []
    for item in items:
        def handler(values):
            return [v for v in values]

        handlers.append(handler)
    return handlers


def compare(a, b):
    return a == b


def send(item, attempt):
    return item, attempt


def read_all(paths):
    rows = []
    for path in paths:
        for row in read_rows(path):
            rows.append(row)
    return rows


def neighbors(graph, nodes):
    for node in nodes:
        for other in graph.get(node, []):
            print(other)


def read_rows(path):
    return [path]
