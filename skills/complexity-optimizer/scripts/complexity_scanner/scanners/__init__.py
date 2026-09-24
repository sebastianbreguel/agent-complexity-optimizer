"""Per-language scanners. `scan_source` picks the AST scanner for Python and regex heuristics for the rest."""

import ast

from ..findings import MODULE_SCOPE, Finding
from .python_ast import scan_python_tree
from .text_heuristics import scan_text


def scan_source(path: str, suffix: str, text: str, lines: list[str]) -> list[Finding]:
    if suffix != ".py":
        return scan_text(path, suffix, lines)
    try:
        return scan_python_tree(path, ast.parse(text))
    except (SyntaxError, ValueError, RecursionError) as exc:
        # Python 2 files, templates, NUL bytes, or expressions too deep for the recursive visitor
        # still get textual leads instead of aborting the whole scan.
        line = getattr(exc, "lineno", None) or 1
        return [Finding(path, line, MODULE_SCOPE, "parse-error", 1, "high"), *scan_text(path, suffix, lines)]
