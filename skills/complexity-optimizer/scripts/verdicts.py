#!/usr/bin/env python3
"""Record whether scanner findings were real, and measure each rule's precision from those verdicts.

Precision is what makes a rule's weight trustworthy: without verdicts, every weight is a guess.
A finding is identified by the scanner's fingerprint `path::function::kind` (the same one --baseline uses).

Usage:
  python3 verdicts.py add ~/.complexity-optimizer/verdicts/shop.jsonl "src/orders.py::load_all::io-or-query-in-loop" confirmed
  python3 verdicts.py report ~/.complexity-optimizer/verdicts/*.jsonl

Verdicts: `confirmed` (real, not fixed yet) and `fixed` count as useful; `false_positive` and
`wont_fix` (real but not worth changing) count as not useful, following Google's Tricorder, where a
warning nobody acts on is an "effective false positive". A finding that merely disappeared from a
later scan is not a verdict: only about half of those were real fixes.
"""

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from complexity_scanner.findings import KINDS

USEFUL = {"confirmed", "fixed"}
NOT_USEFUL = {"false_positive", "wont_fix"}
Z_95 = 1.96
# Starting precision before any verdict, weighed as PRIOR_WEIGHT verdicts: Python is parsed (AST),
# other languages go through line heuristics. Both values are judgment calls, replaced by data as verdicts arrive.
PRIOR_PRECISION = {"ast": 0.8, "regex": 0.6}
PRIOR_WEIGHT = 10
# Tricorder's thresholds on the not-useful rate: over 10% puts a check on probation, over 25% turns it off.
PROBATION_RATE = 0.10
OFF_RATE = 0.25
MIN_VERDICTS = 10


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
    """95% interval for a proportion; unlike the plain p ± 2σ, it stays honest for small samples and rates near 0 or 1."""
    if total == 0:
        return 0.0, 1.0
    p = successes / total
    center = (p + Z_95**2 / (2 * total)) / (1 + Z_95**2 / total)
    margin = Z_95 * math.sqrt(p * (1 - p) / total + Z_95**2 / (4 * total**2)) / (1 + Z_95**2 / total)
    return max(0.0, center - margin), min(1.0, center + margin)


def status(not_useful: int, total: int) -> str:
    if total < MIN_VERDICTS:
        return f"needs data ({total}/{MIN_VERDICTS})"
    low, _ = wilson_interval(not_useful, total)
    return "off" if low > OFF_RATE else "probation" if low > PROBATION_RATE else "active"


def prior_adjusted_precision(useful: int, total: int, parser: str) -> float:
    return (PRIOR_WEIGHT * PRIOR_PRECISION[parser] + useful) / (PRIOR_WEIGHT + total)


def split_fingerprint(fingerprint: str) -> tuple[str, str]:
    """(path, kind) of `path::function::kind`; the function name itself may contain `::`."""
    location, _, kind = fingerprint.rpartition("::")
    if "::" not in location:
        raise ValueError(f"expected path::function::kind, got {fingerprint!r}")
    return location.split("::", 1)[0], kind


def read_record(line: str) -> dict:
    # The kind isn't checked against today's rules: verdicts on a renamed or removed rule still count.
    record = json.loads(line)
    split_fingerprint(record["fingerprint"])
    if record["verdict"] not in USEFUL | NOT_USEFUL:
        raise ValueError(f"unknown verdict {record['verdict']!r}")
    return record


def latest_verdicts(files: list[Path]) -> list[dict]:
    """The last verdict per fingerprint in each file wins; files stay separate so equal paths in two repos don't collide."""
    latest = []
    for file in files:
        by_fingerprint = {}
        for number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = read_record(line)
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"{file}:{number}: {type(exc).__name__}: {exc}") from exc
            by_fingerprint[record["fingerprint"]] = record
        latest += by_fingerprint.values()
    return latest


def report(files: list[Path]) -> str:
    counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for record in latest_verdicts(files):
        path, kind = split_fingerprint(record["fingerprint"])
        tally = counts[(kind, Path(path).suffix)]
        tally[0] += record["verdict"] in USEFUL
        tally[1] += 1
    lines = [
        "| Rule | Language | Verdicts | Useful | Precision (with prior) | Not-useful rate, 95% CI | Status |",
        "|------|----------|----------|--------|------------------------|-------------------------|--------|",
    ]
    for (kind, suffix), (useful, total) in sorted(counts.items()):
        low, high = wilson_interval(total - useful, total)
        precision = prior_adjusted_precision(useful, total, "ast" if suffix == ".py" else "regex")
        lines.append(
            f"| {kind} | {suffix} | {total} | {useful} | {precision:.2f} | {low:.2f}-{high:.2f} | {status(total - useful, total)} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record verdicts on scanner findings and report precision per rule.")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="Append a verdict for one finding.")
    add.add_argument("file", type=Path)
    add.add_argument("fingerprint", help="path::function::kind, as the scanner reports it")
    add.add_argument("verdict", choices=sorted(USEFUL | NOT_USEFUL))
    show = commands.add_parser("report", help="Precision per rule and language.")
    show.add_argument("files", type=Path, nargs="+")
    args = parser.parse_args()

    if args.command == "add":
        try:
            _, kind = split_fingerprint(args.fingerprint)
        except ValueError as exc:
            parser.error(str(exc))
        if kind not in KINDS:
            parser.error(f"unknown rule {kind!r}; the scanner's rules are {', '.join(sorted(KINDS))}")
        record = {"fingerprint": args.fingerprint, "verdict": args.verdict, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        args.file.parent.mkdir(parents=True, exist_ok=True)
        with args.file.open("a", encoding="utf-8") as out:
            out.write(json.dumps(record) + "\n")
        return 0
    try:
        print(report(args.files))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
