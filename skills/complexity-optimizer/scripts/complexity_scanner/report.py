"""Render a scan as markdown (for people and agents) or JSON (for tools)."""

import json
from dataclasses import asdict, dataclass

from .baseline import BaselineDiff
from .findings import Finding
from .ranking import Hotspot


GENERATED_SHOWN = 5


@dataclass
class Report:
    scanned_files: int
    scanned_lines: int
    skipped: dict[str, int]
    generated_files: list[str]  # listed so a wrongly skipped hand-written file is easy to spot
    health: int | None
    health_label: str
    total_findings: int
    baseline: BaselineDiff | None
    hotspots: list[Hotspot]
    findings: list[Finding]


def render_json(report: Report) -> str:
    return json.dumps(asdict(report), indent=2)


def summary_lines(report: Report) -> list[str]:
    shown = len(report.findings)
    health = f"{report.health}/100 ({report.health_label})" if report.health is not None else report.health_label
    lines = [
        f"**Health: {health}** · "
        f"{report.scanned_files} files, {report.scanned_lines:,} lines scanned · {report.total_findings} findings"
        + (f" (showing the top {shown} by score; raise --max-findings for more)" if report.total_findings > shown else "")
    ]
    skipped = []
    if report.skipped["tests"]:
        skipped.append(f"{report.skipped['tests']} test files (use --include-tests)")
    if report.generated_files:
        listed = ", ".join(f"`{path}`" for path in report.generated_files[:GENERATED_SHOWN])
        more = f" and {len(report.generated_files) - GENERATED_SHOWN} more" if len(report.generated_files) > GENERATED_SHOWN else ""
        skipped.append(f"{len(report.generated_files)} generated/minified files ({listed}{more})")
    if skipped:
        lines.append("Skipped: " + ", ".join(skipped) + ".")
    if report.baseline:
        lines.append(f"Baseline: {report.baseline.new} new, {report.baseline.fixed} fixed.")
    return lines


def render_markdown(report: Report) -> str:
    lines = ["# Complexity Hotspots", "", *summary_lines(report), ""]
    if not report.findings:
        return "\n".join(lines + ["No obvious complexity hotspots found by heuristic scanning.", ""])

    lines += ["## Top functions", "", "| # | Function | Location | Score | Findings |", "|---|----------|----------|-------|----------|"]
    for i, spot in enumerate(report.hotspots, start=1):
        kinds = ", ".join(f"{kind} x{count}" if count > 1 else kind for kind, count in spot.kinds.items())
        lines.append(f"| {i} | `{spot.function}` | `{spot.path}:{spot.line}` | {spot.score} | {kinds} |")

    lines += ["", "## Findings", ""]
    for i, f in enumerate(report.findings, start=1):
        status = " · NEW" if f.status == "new" else ""
        tags = f"score {f.score} · confidence {f.confidence} · loop depth {f.depth}"
        if f.context == "one-off":
            tags += " · one-off path (ranked lower)"
        lines += [f"### {i}. {f.severity.upper()} {f.kind} · `{f.path}:{f.line}` · `{f.function}`{status}", ""]
        if f.code:
            lines += [f"    {f.code}", ""]
        lines += [f"- Finding: {f.message}", f"- Suggestion: {f.suggestion}", f"- {tags}", ""]
    lines.append("Findings are leads, not proof: check how large the input gets and how often the code runs, then measure.")
    return "\n".join(lines) + "\n"
