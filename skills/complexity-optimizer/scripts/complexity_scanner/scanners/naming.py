"""Naming conventions that reveal intent the syntax alone can't: batches, retries, maps, constants."""

import re

# Loops over chunks/batches/pages are usually the batching fix already applied.
BATCH_NAME_RE = re.compile(r"(?:chunk|batch|page)(?:s|ed|_?size)?$", re.IGNORECASE)
# `for attempt in range(max_retries)` repeats one operation; it doesn't walk data.
RETRY_NAME_RE = re.compile(r"attempt|retr(?:y|ies)|tries", re.IGNORECASE)
# A function that says it runs things in order means the sequential awaits are intended.
SEQUENTIAL_NAME_RE = re.compile(r"sequential|serial|in_order|inOrder", re.IGNORECASE)
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
    return bool(BATCH_NAME_RE.search(name))


def is_retry_name(name: str) -> bool:
    return bool(RETRY_NAME_RE.search(name))
