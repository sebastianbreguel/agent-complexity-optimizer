"""End-to-end tests of analyze_complexity.py: file selection, ranking, output formats, CI flags."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCANNER = Path(__file__).resolve().parent.parent / "skills" / "complexity-optimizer" / "scripts" / "analyze_complexity.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_scanner(target: Path, *flags: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run([sys.executable, str(SCANNER), str(target), *flags], capture_output=True, text=True)
    if check:
        assert result.returncode == 0, f"Scanner failed: {result.stderr}"
    return result


def scan_json(target: Path, *flags: str) -> dict:
    return json.loads(run_scanner(target, "--format", "json", "--max-findings", "1000", *flags).stdout)


def kinds_for(report: dict, filename: str) -> set[str]:
    return {f["kind"] for f in report["findings"] if f["path"].endswith(filename)}


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "test")
    (tmp_path / "old.py").write_text("def f(a, b):\n    for x in a:\n        for y in b:\n            print(x, y)\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


class TestFixtures:
    def test_detects_each_fixture_pattern(self):
        report = scan_json(FIXTURES)
        assert "nested-loop" in kinds_for(report, "nested_loops.py")
        assert "nested-loop" in kinds_for(report, "nested_loops.js")
        assert kinds_for(report, "n_plus_one.py") == {"io-or-query-in-loop"}
        assert "membership-in-loop" in kinds_for(report, "membership_in_loop.py")
        assert "sort-in-loop" in kinds_for(report, "sort_in_loop.py")
        assert "render-derived-work" in kinds_for(report, "render_path.tsx")

    def test_clean_code_has_no_findings(self):
        report = scan_json(FIXTURES)
        for clean in ("clean_code.py", "clean_code.js", "constants_module.ts"):
            assert not kinds_for(report, clean), clean

    def test_render_zone_closes_at_component_end(self):
        report = scan_json(FIXTURES)
        lines = [f["line"] for f in report["findings"] if f["path"].endswith("render_path.tsx")]
        assert lines and all(line <= 4 for line in lines), lines

    def test_confidence_follows_the_scanner(self):
        report = scan_json(FIXTURES)
        assert {f["confidence"] for f in report["findings"] if f["path"].endswith(".py")} == {"high"}
        assert {f["confidence"] for f in report["findings"] if f["path"].endswith(".js")} == {"low"}


class TestFileSelection:
    def test_tests_are_skipped_by_default(self):
        report = scan_json(FIXTURES)
        assert not any("__tests__" in f["path"] for f in report["findings"])
        assert report["skipped"]["tests"] >= 1

    def test_include_tests(self):
        report = scan_json(FIXTURES, "--include-tests")
        assert any("__tests__" in f["path"] for f in report["findings"])

    def test_minified_files_are_skipped(self):
        report = scan_json(FIXTURES)
        assert not any(f["path"].endswith(".min.js") for f in report["findings"])
        assert report["skipped"]["generated"] >= 1

    def test_gitignored_files_are_skipped(self, repo: Path):
        (repo / ".gitignore").write_text("build_output/\n")
        (repo / "build_output").mkdir()
        (repo / "build_output" / "bundle.py").write_text((repo / "old.py").read_text())
        report = scan_json(repo)
        assert {f["path"] for f in report["findings"]} == {"old.py"}

    def test_changed_only_scans_the_diff(self, repo: Path):
        (repo / "new.py").write_text("def g(ids, db):\n    for i in ids:\n        db.query(i)\n")
        report = scan_json(repo, "--changed", "main")
        assert {f["path"] for f in report["findings"]} == {"new.py"}

    def test_changed_with_unknown_base_fails_cleanly(self, repo: Path):
        result = run_scanner(repo, "--changed", "no-such-branch", check=False)
        assert result.returncode == 2
        assert "--changed" in result.stderr


class TestRanking:
    def test_findings_are_sorted_by_score(self):
        scores = [f["score"] for f in scan_json(FIXTURES)["findings"]]
        assert scores == sorted(scores, reverse=True)

    def test_io_outranks_membership(self):
        findings = scan_json(FIXTURES)["findings"]
        score = {f["kind"]: f["score"] for f in findings}
        assert score["io-or-query-in-loop"] > score["membership-in-loop"]

    def test_hotspots_group_by_function(self):
        hotspots = scan_json(FIXTURES)["hotspots"]
        assert {"load_all_profiles", "fetch_avatars", "find_matches"} <= {h["function"] for h in hotspots}

    def test_one_off_paths_rank_lower(self, repo: Path):
        (repo / "scripts").mkdir()
        (repo / "scripts" / "backfill.py").write_text((repo / "old.py").read_text())
        findings = {f["path"]: f for f in scan_json(repo)["findings"]}
        assert findings["scripts/backfill.py"]["context"] == "one-off"
        assert findings["scripts/backfill.py"]["score"] < findings["old.py"]["score"]

    def test_suppression_comment(self, repo: Path):
        (repo / "old.py").write_text(
            "def f(a, b):\n    for x in a:\n        for y in b:  # complexity: ignore (tiny)\n            print(x, y)\n"
        )
        assert scan_json(repo)["findings"] == []

    def test_health_drops_with_findings(self, repo: Path):
        clean = repo / "clean"
        clean.mkdir()
        (clean / "ok.py").write_text("def f(a):\n    return sum(a)\n")
        assert scan_json(clean)["health"] == 100
        assert scan_json(repo)["health"] < 100


class TestOutput:
    def test_json_shape(self):
        report = scan_json(FIXTURES)
        assert {"scanned_files", "scanned_lines", "skipped", "health", "health_label", "total_findings", "hotspots", "findings"} <= set(
            report
        )
        expected = {
            "path",
            "line",
            "function",
            "kind",
            "severity",
            "score",
            "confidence",
            "depth",
            "context",
            "code",
            "message",
            "suggestion",
        }
        assert all(expected <= set(f) for f in report["findings"])

    def test_markdown_report(self):
        output = run_scanner(FIXTURES).stdout
        assert "# Complexity Hotspots" in output
        assert "**Health:" in output
        assert "## Top functions" in output
        assert "db.query(" in output  # code snippet of the finding

    def test_max_findings_keeps_hotspots_complete(self):
        report = scan_json(FIXTURES, "--max-findings", "1")
        assert len(report["findings"]) == 1
        assert len(report["hotspots"]) > 1


class TestCiFlags:
    def test_fail_on_high(self, repo: Path):
        assert run_scanner(repo, "--fail-on", "high", check=False).returncode == 1
        (repo / "old.py").write_text("def f(a):\n    return sum(a)\n")
        assert run_scanner(repo, "--fail-on", "high", check=False).returncode == 0

    def test_baseline_reports_new_and_fixed(self, repo: Path):
        baseline = repo / "baseline.json"
        run_scanner(repo, "--write-baseline", str(baseline))
        (repo / "new.py").write_text("def g(ids, db):\n    for i in ids:\n        db.query(i)\n")
        (repo / "old.py").write_text("def f(a):\n    return sum(a)\n")
        report = scan_json(repo, "--baseline", str(baseline))
        assert report["baseline"] == {"new": 1, "fixed": 1}
        assert [f["status"] for f in report["findings"]] == ["new"]

    def test_fail_on_ignores_known_findings(self, repo: Path):
        baseline = repo / "baseline.json"
        run_scanner(repo, "--write-baseline", str(baseline))
        assert run_scanner(repo, "--baseline", str(baseline), "--fail-on", "high", check=False).returncode == 0
        (repo / "new.py").write_text("def g(ids, db):\n    for i in ids:\n        db.query(i)\n")
        assert run_scanner(repo, "--baseline", str(baseline), "--fail-on", "high", check=False).returncode == 1

    def test_baseline_survives_line_shifts(self, repo: Path):
        baseline = repo / "baseline.json"
        run_scanner(repo, "--write-baseline", str(baseline))
        (repo / "old.py").write_text("import os\n\n\n" + (repo / "old.py").read_text())
        assert scan_json(repo, "--baseline", str(baseline))["baseline"] == {"new": 0, "fixed": 0}
