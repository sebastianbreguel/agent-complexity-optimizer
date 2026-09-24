"""Score findings, keep the strongest one per line, and surface the functions most likely to be bottlenecks."""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from .findings import KINDS, SEVERITY_ORDER, Finding

CONFIDENCE_FACTOR = {"high": 1.0, "low": 0.6}
# Code that runs once (migrations, seeds, scripts) still gets reported, but ranked lower.
ONE_OFF_PATH_RE = re.compile(r"(^|/)(migrations?|data-migrations|seeds?|seeders|scripts|examples?|benchmarks?|demo)/")
ONE_OFF_FACTOR = 0.3
SUPPRESS_RE = re.compile(r"complexity:\s*ignore")
CODE_SNIPPET_LENGTH = 120
HOTSPOT_LIMIT = 10
# Findings in one function are correlated evidence (a confirmed one makes its siblings likely real too), so a
# hotspot scores its strongest finding plus this share per extra distinct pattern instead of the sum:
# five membership checks shouldn't outrank one N+1 query.
EXTRA_KIND_BONUS = 0.1


@dataclass
class Hotspot:
    path: str
    function: str
    line: int
    score: float
    findings: int
    kinds: dict[str, int]


def annotate(findings: list[Finding], lines: list[str]) -> list[Finding]:
    """Fill severity, message, code snippet and score; drop lines marked `complexity: ignore`."""
    kept = []
    for finding in findings:
        source = lines[finding.line - 1] if 0 < finding.line <= len(lines) else ""
        if SUPPRESS_RE.search(source):
            continue
        kind = KINDS[finding.kind]
        finding.severity, finding.message, finding.suggestion = kind.severity, kind.message, kind.suggestion
        finding.code = source.strip()[:CODE_SNIPPET_LENGTH]
        finding.context = "one-off" if ONE_OFF_PATH_RE.search(finding.path) else "app"
        score = kind.weight * finding.depth * CONFIDENCE_FACTOR[finding.confidence]
        finding.score = round(score * (ONE_OFF_FACTOR if finding.context == "one-off" else 1.0), 1)
        kept.append(finding)
    return kept


def rank(findings: list[Finding]) -> list[Finding]:
    """Highest score first, one finding per line (the strongest one)."""
    ordered = sorted(findings, key=lambda f: (-f.score, SEVERITY_ORDER[f.severity], f.path, f.line))
    seen: set[tuple[str, int]] = set()
    result = []
    for finding in ordered:
        if (finding.path, finding.line) not in seen:
            seen.add((finding.path, finding.line))
            result.append(finding)
    return result


def hotspot_score(group: list[Finding]) -> float:
    extra_kinds = len({f.kind for f in group}) - 1
    return max(f.score for f in group) * (1 + EXTRA_KIND_BONUS * extra_kinds)


def hotspots(findings: list[Finding], limit: int = HOTSPOT_LIMIT) -> list[Hotspot]:
    groups: dict[tuple[str, str], list[Finding]] = defaultdict(list)
    for finding in findings:
        if finding.score > 0:
            groups[(finding.path, finding.function)].append(finding)
    spots = [
        Hotspot(
            path=path,
            function=function,
            line=min(f.line for f in group),
            score=round(hotspot_score(group), 1),
            findings=len(group),
            kinds=dict(Counter(f.kind for f in group).most_common()),
        )
        for (path, function), group in groups.items()
    ]
    return sorted(spots, key=lambda spot: (-spot.score, -spot.findings, spot.path, spot.function))[:limit]


def density(findings: list[Finding], scanned_lines: int) -> float:
    """Score points per 1,000 scanned lines, comparable across repos and over time (lower is better).

    Deliberately not a 0-100 grade with healthy/critical labels: no study ties this kind of density
    to real slowness, so it tracks progress but is not a quality verdict."""
    return round(sum(f.score for f in findings) / max(1.0, scanned_lines / 1000), 1)
