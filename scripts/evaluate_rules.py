#!/usr/bin/env python3
"""Measure the scanner's precision and recall per rule against labeled code.

Label lines in tests/cases/** (or any corpus passed with --cases) with a trailing comment:

  expect: <kind>    the scanner must report <kind> on this line
  todo: <kind>      it should, but doesn't yet (counted as a miss; tests tolerate it)
  todo-fp: <kind>   it reports <kind> here but shouldn't (counted as a false positive; tests tolerate it)

Any other reported line is an unexpected false positive. A `todo` that starts passing, or a
`todo-fp` that stops firing, is reported as stale so the labels keep up with the scanner.

Usage:
  python3 scripts/evaluate_rules.py               # per-rule table, then every problem
  python3 scripts/evaluate_rules.py --cases DIR   # evaluate another labeled corpus
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCANNER = ROOT / "skills" / "complexity-optimizer" / "scripts" / "analyze_complexity.py"
DEFAULT_CASES = ROOT / "tests" / "cases"
MARKER_RE = re.compile(r"\b(expect|todo-fp|todo):\s*([a-z0-9-]+)")


@dataclass
class Evaluation:
    true_positives: Counter = field(default_factory=Counter)
    false_positives: Counter = field(default_factory=Counter)
    false_negatives: Counter = field(default_factory=Counter)
    misses: list[str] = field(default_factory=list)  # `expect` lines the scanner got wrong
    unexpected: list[str] = field(default_factory=list)  # reported lines nobody labeled
    known_misses: list[str] = field(default_factory=list)
    known_false_positives: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not (self.misses or self.unexpected or self.stale)


def load_markers(cases: Path) -> dict[tuple[str, int], tuple[str, str]]:
    markers = {}
    for path in sorted(p for p in cases.rglob("*") if p.is_file()):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = MARKER_RE.search(line)
            if match:
                markers[(path.relative_to(cases).as_posix(), number)] = (match.group(1), match.group(2))
    return markers


def scan(cases: Path) -> dict[tuple[str, int], str]:
    command = [sys.executable, str(SCANNER), str(cases), "--format", "json", "--max-findings", "1000000", "--include-tests"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"scanner failed on {cases}:\n{result.stderr}")
    return {(f["path"], f["line"]): f["kind"] for f in json.loads(result.stdout)["findings"]}


def evaluate(cases: Path = DEFAULT_CASES) -> Evaluation:
    markers = load_markers(cases)
    reported = scan(cases)
    result = Evaluation()
    for key, (marker, kind) in sorted(markers.items()):
        got = reported.get(key)
        where = f"{key[0]}:{key[1]}"
        if marker == "expect" and got == kind:
            result.true_positives[kind] += 1
        elif marker == "expect":
            result.false_negatives[kind] += 1
            result.misses.append(f"{where} expected {kind}, got {got or 'nothing'}")
        elif marker == "todo" and got == kind:
            result.stale.append(f"{where} `todo: {kind}` is detected now; change it to `expect:`")
        elif marker == "todo":
            result.false_negatives[kind] += 1
            result.known_misses.append(f"{where} {kind}")
        elif got == kind:  # todo-fp still firing
            result.false_positives[kind] += 1
            result.known_false_positives.append(f"{where} {kind}")
        else:
            result.stale.append(f"{where} `todo-fp: {kind}` no longer fires; remove the marker")
        if got and got != kind:
            result.false_positives[got] += 1
            if marker != "expect":
                result.unexpected.append(f"{where} unexpected {got}")
    for key, got in sorted(reported.items()):
        if key not in markers:
            result.false_positives[got] += 1
            result.unexpected.append(f"{key[0]}:{key[1]} unexpected {got}")
    return result


def ratio(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator:.0%}" if denominator else "—"


def render(result: Evaluation) -> str:
    kinds = sorted(set(result.true_positives) | set(result.false_positives) | set(result.false_negatives))
    lines = [f"{'rule':<24} {'TP':>4} {'FP':>4} {'FN':>4} {'precision':>10} {'recall':>8}"]
    for kind in kinds:
        tp, fp, fn = result.true_positives[kind], result.false_positives[kind], result.false_negatives[kind]
        lines.append(f"{kind:<24} {tp:>4} {fp:>4} {fn:>4} {ratio(tp, tp + fp):>10} {ratio(tp, tp + fn):>8}")
    tp, fp, fn = (sum(c.values()) for c in (result.true_positives, result.false_positives, result.false_negatives))
    lines.append(f"{'total':<24} {tp:>4} {fp:>4} {fn:>4} {ratio(tp, tp + fp):>10} {ratio(tp, tp + fn):>8}")
    sections = [
        ("Missed `expect` labels", result.misses),
        ("Unexpected findings (false positives)", result.unexpected),
        ("Stale labels", result.stale),
        ("Known misses (todo)", result.known_misses),
        ("Known false positives (todo-fp)", result.known_false_positives),
    ]
    for title, items in sections:
        if items:
            lines += ["", f"{title}:", *(f"  {item}" for item in items)]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Per-rule precision/recall of the scanner on labeled cases.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES, help="Directory with labeled source files.")
    args = parser.parse_args()
    result = evaluate(args.cases.resolve())
    print(render(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
