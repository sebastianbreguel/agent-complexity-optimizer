"""Compare a scan with a saved baseline: fixed findings show progress, and only new ones need to fail CI.

Findings are matched by (path, function, kind) instead of line number, so unrelated edits that
shift lines don't turn old findings into "new" ones.
"""

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .findings import Finding

BASELINE_VERSION = 1


@dataclass
class BaselineDiff:
    new: int
    fixed: int


def fingerprint(finding: Finding) -> str:
    return f"{finding.path}::{finding.function}::{finding.kind}"


def write_baseline(path: Path, findings: list[Finding]) -> None:
    counts = Counter(fingerprint(f) for f in findings)
    path.write_text(
        json.dumps({"version": BASELINE_VERSION, "fingerprints": dict(sorted(counts.items()))}, indent=2) + "\n", encoding="utf-8"
    )


def read_baseline(path: Path) -> Counter:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != BASELINE_VERSION:
        raise ValueError(f"unsupported baseline version {data.get('version')!r} in {path}")
    return Counter(data["fingerprints"])


def mark_new(findings: list[Finding], baseline: Counter) -> BaselineDiff:
    """Set `status` on every finding; per fingerprint, the first N (in file order) are the known ones."""
    seen: Counter = Counter()
    for finding in sorted(findings, key=lambda f: (f.path, f.line)):
        key = fingerprint(finding)
        seen[key] += 1
        finding.status = "known" if seen[key] <= baseline[key] else "new"
    fixed = sum(max(0, count - seen[key]) for key, count in baseline.items())
    return BaselineDiff(new=sum(f.status == "new" for f in findings), fixed=fixed)
