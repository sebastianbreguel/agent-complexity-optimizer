"""Per-language scanners. `scan_source` picks the AST scanner for Python and regex heuristics for the rest."""

import ast

from ..findings import MODULE_SCOPE, Finding
from .python_ast import scan_python_tree
from .text_heuristics import scan_text


def scan_source(path: str, suffix: str, text: str, lines: list[str]) -> list[Finding]:
    if suffix != ".py":
        return scan_text(path, suffix, lines)
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        # A file that doesn't parse (Python 2, templates) still gets textual leads.
        return [Finding(path, exc.lineno or 1, MODULE_SCOPE, "parse-error", 1, "high"), *scan_text(path, suffix, lines)]
    return scan_python_tree(path, tree)
