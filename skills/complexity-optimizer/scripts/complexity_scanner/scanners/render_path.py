"""React-style component detection: code in a function component's body re-runs on every render."""

import re

RENDER_SUFFIXES = {".jsx", ".tsx", ".js", ".ts"}
# Component names need at least one lowercase letter (PascalCase) so UPPER_CASE constants
# don't open a component zone; const-form additionally requires a function-looking right side.
COMPONENT_HEADER_RE = re.compile(
    r"\bfunction\s+[A-Z]\w*[a-z]\w*\s*\("
    r"|\bconst\s+[A-Z]\w*[a-z]\w*\s*=\s*(?:async\s+)?(?:\(|function\b|React\.|memo\s*\(|forwardRef\s*\(|styled[.(]|[A-Za-z_$][\w$]*\s*=>)"
)
# `.map` alone is how lists get rendered; filtering/sorting/reducing is derived work worth memoizing.
RENDER_TRANSFORM_RE = re.compile(r"\.(?:filter|sort|toSorted|reduce)\(")
MEMOIZED_RE = re.compile(r"\buse(?:Memo|Callback)\s*\(")
COMPONENT_ZONE_MAX_LINES = 120


def render_path_lines(lines: list[str]) -> set[int]:
    """Line numbers inside likely component bodies, excluding lines already wrapped in useMemo/useCallback."""
    active_until = 0
    interesting: set[int] = set()
    brace_balance = 0
    in_component = False
    memo_until_balance: int | None = None

    for idx, line in enumerate(lines, start=1):
        if COMPONENT_HEADER_RE.search(line):
            in_component = True
            active_until = idx + COMPONENT_ZONE_MAX_LINES
            brace_balance = 0
            memo_until_balance = None
        if not in_component:
            continue
        if MEMOIZED_RE.search(line) and memo_until_balance is None:
            memo_until_balance = brace_balance
        if memo_until_balance is None:
            interesting.add(idx)
        brace_balance += line.count("{") - line.count("}") + line.count("(") - line.count(")")
        if memo_until_balance is not None and brace_balance <= memo_until_balance:
            memo_until_balance = None
        # Close the zone as soon as the component's braces balance out, so code below a small
        # component doesn't inherit its render-path findings; cap as a fallback.
        if idx > active_until or (brace_balance <= 0 and ("}" in line or ")" in line)):
            in_component = False
    return interesting
