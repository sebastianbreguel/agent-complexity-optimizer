"""Naming conventions that reveal intent the syntax alone can't: batches, retries, maps, constants.

Names are compared by whole tokens (`userRepository` -> user, repository), never substrings:
`entries` is not a retry and `webpage` is not a page of results.
"""

import re

# A loop over chunks/batches/pages is usually the batching fix already applied.
BATCH_TOKENS = {"chunk", "chunks", "chunked", "batch", "batches", "batched", "page", "pages", "paginate", "paginated"}
BATCH_SIZE_PREFIXES = {"chunk", "batch", "page"}  # `batch_size`, `pageSize`: a loop stepping by it walks batches
# `for attempt in range(max_retries)` repeats one operation; it doesn't walk data.
RETRY_TOKENS = {"attempt", "attempts", "retry", "retries", "tries"}
# A function that says it runs things in order means the sequential awaits are intended.
SEQUENTIAL_TOKENS = {"sequential", "sequentially", "serial", "serially"}
# `users_by_id`, `tgt_map`, `seenIds`: names people give to dicts/sets, where lookups are O(1).
HASHED_NAME_TOKENS = {"map", "dict", "set", "lookup", "index", "cache", "registry", "counter", "counts", "seen", "visited"}
HASHED_PREFIX_TOKENS = {"seen", "visited"}
UPPER_CONSTANT_RE = re.compile(r"^[A-Z][A-Z0-9_]*[A-Z0-9]$")


def name_tokens(name: str) -> list[str]:
    """`userRepository` -> ["user", "repository"], `db_session` -> ["db", "session"]."""
    return [token.lower() for token in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", name)]


def is_hashed_name(name: str) -> bool:
    tokens = name_tokens(name)
    return bool(tokens) and (tokens[-1] in HASHED_NAME_TOKENS or tokens[0] in HASHED_PREFIX_TOKENS or "by" in tokens[1:-1])


def is_constant_name(name: str) -> bool:
    """UPPER_CASE names are fixed, code-sized collections: scanning them doesn't grow with input."""
    return bool(UPPER_CONSTANT_RE.match(name))


def is_batch_name(name: str) -> bool:
    tokens = name_tokens(name)
    return bool(tokens) and tokens[-1] in BATCH_TOKENS


def is_batch_size_name(name: str) -> bool:
    tokens = name_tokens(name)
    return len(tokens) > 1 and tokens[-1] == "size" and tokens[-2] in BATCH_SIZE_PREFIXES


def is_retry_name(name: str) -> bool:
    return bool(RETRY_TOKENS & set(name_tokens(name)))


def is_sequential_name(name: str) -> bool:
    tokens = name_tokens(name)
    return bool(SEQUENTIAL_TOKENS & set(tokens)) or any(a == "in" and b == "order" for a, b in zip(tokens, tokens[1:]))
