"""Command line: pick files, scan them, rank the findings, print the report, set the exit code."""

import argparse
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .baseline import mark_new, read_baseline, write_baseline
from .discovery import DEFAULT_EXCLUDES, changed_source_files, is_generated, is_test_path, list_source_files, read_text
from .findings import SEVERITY_ORDER, Finding
from .ranking import annotate, density, hotspots, rank
from .report import Report, render_json, render_markdown
from .scanners import scan_source


def parse_args(argv: list[str] | None) -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    parser = argparse.ArgumentParser(description="Scan a repository for likely complexity hotspots, ranked by score.")
    parser.add_argument("root", nargs="?", default=".", help="Repository or directory to scan.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--exclude", action="append", default=[], help="Additional directory name to exclude.")
    parser.add_argument("--max-findings", type=int, default=50, help="Findings to list (hotspots and density use all of them).")
    parser.add_argument("--include-tests", action="store_true", help="Also scan test files (skipped by default).")
    parser.add_argument("--changed", metavar="BASE", help="Only scan files changed since the merge-base with BASE (e.g. main).")
    parser.add_argument(
        "--fail-on", choices=["high", "medium"], help="Exit 1 if a finding (a new one, with --baseline) has at least this severity."
    )
    parser.add_argument("--baseline", type=Path, metavar="FILE", help="Compare with a baseline written by --write-baseline.")
    parser.add_argument("--write-baseline", type=Path, metavar="FILE", help="Save all current findings as the baseline.")
    return parser, parser.parse_args(argv)


@dataclass
class ScanResult:
    findings: list[Finding] = field(default_factory=list)
    scanned_paths: set[str] = field(default_factory=set)
    scanned_lines: int = 0
    skipped_tests: int = 0
    generated_paths: list[str] = field(default_factory=list)


def scan_files(root: Path, paths: list[Path], include_tests: bool) -> ScanResult:
    result = ScanResult()
    for path in paths:
        relpath = path.relative_to(root).as_posix()
        if not include_tests and is_test_path(relpath):
            result.skipped_tests += 1
            continue
        text = read_text(path)
        if text is None:
            continue
        lines = text.splitlines()
        if is_generated(path, lines):
            result.generated_paths.append(relpath)
            continue
        result.scanned_paths.add(relpath)
        result.scanned_lines += sum(1 for line in lines if line.strip())
        result.findings += annotate(scan_source(relpath, path.suffix, text, lines), lines)
    return result


def main(argv: list[str] | None = None) -> int:
    parser, args = parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error(f"{args.root} is not a directory")
    excludes = DEFAULT_EXCLUDES | set(args.exclude)
    try:
        paths = changed_source_files(root, args.changed, excludes) if args.changed else list_source_files(root, excludes)
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError) as exc:
        parser.error(f"--changed {args.changed}: {getattr(exc, 'stderr', '') or exc}".strip())

    scan = scan_files(root, paths, args.include_tests)
    ranked = rank(scan.findings)
    try:
        diff = mark_new(ranked, read_baseline(args.baseline), scan.scanned_paths) if args.baseline else None
    except (OSError, ValueError, KeyError) as exc:
        parser.error(f"--baseline {args.baseline}: {exc}")
    if args.baseline:
        ranked.sort(key=lambda f: f.status == "known")  # new findings first, score order kept within each group
    if args.write_baseline:
        write_baseline(args.write_baseline, ranked)

    report = Report(
        scanned_files=len(scan.scanned_paths),
        scanned_lines=scan.scanned_lines,
        skipped={"tests": scan.skipped_tests, "generated": len(scan.generated_paths)},
        generated_files=scan.generated_paths,
        density=None if args.changed else density(ranked, scan.scanned_lines),
        total_findings=len(ranked),
        baseline=diff,
        hotspots=hotspots(ranked),
        findings=ranked[: args.max_findings],
    )
    print(render_json(report) if args.format == "json" else render_markdown(report).rstrip("\n"))

    if args.fail_on:
        gated = [f for f in ranked if f.status != "known"]
        if any(SEVERITY_ORDER[f.severity] <= SEVERITY_ORDER[args.fail_on] for f in gated):
            return 1
    return 0
