from dataclasses import dataclass, field

ALLOWED = {"a", "b"}


def banned(items, banned_names):
    return [i for i in items if i.name not in banned_names]  # expect: membership-in-loop


def typed(items, seen: set[str], lookup: dict[str, int], maybe: set[str] | None):
    out = []
    for item in items:
        if item in seen or item in lookup or item in ALLOWED or item in maybe:
            out.append(item)
    return out


def local_set(items, ids):
    known = set(ids)
    return [i for i in items if i in known]


def element_local(rows):
    for row in rows:
        if "x" in row:
            print(row)


def literal_choices(rows):
    for row in rows:
        if row.status in ("active", "pending"):
            print(row)


def dict_keys(items, mapping):
    for item in items:
        if item in mapping.keys():
            print(item)


class Tracker:
    def __init__(self):
        self.seen = set()
        self.order = []

    def add_all(self, items):
        for item in items:
            if item not in self.seen:
                self.seen.add(item)
            if item in self.order:  # expect: membership-in-loop
                print(item)


@dataclass
class Registry:
    names: set[str] = field(default_factory=set)

    def known(self, items):
        return [i for i in items if i in self.names]


def index_lookup(items, order):
    return sorted(items, key=lambda x: order.index(x))  # expect: membership-in-loop


def list_remove(items, pending):
    for item in items:
        pending.remove(item)  # expect: membership-in-loop


def string_search(lines):
    for line in lines:
        print(line.index(":"))


def named_maps(items, users_by_id, tgt_map, seen_ids):
    return [i for i in items if i.id in users_by_id or i.id in tgt_map or i.id in seen_ids]


SUPPORTED = ["a", "b", "c"]


def constant_list(items):
    return [i for i in items if i.kind in SUPPORTED]


def existing_ids(rows) -> set[str]:
    return {r.id for r in rows}


def only_new(items, rows):
    existing = existing_ids(rows)
    return [i for i in items if i.id not in existing]
