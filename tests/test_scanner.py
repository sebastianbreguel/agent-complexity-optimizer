"""Tests for analyze_complexity.py scanner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCANNER = Path(__file__).resolve().parent.parent / "skills" / "complexity-optimizer" / "scripts" / "analyze_complexity.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_scanner(fixture_dir: str | Path, fmt: str = "json") -> list[dict]:
    result = subprocess.run(
        [sys.executable, str(SCANNER), str(fixture_dir), "--format", fmt],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Scanner failed: {result.stderr}"
    if fmt == "json":
        return json.loads(result.stdout)
    return result.stdout


def findings_for_file(filename: str) -> list[dict]:
    all_findings = run_scanner(FIXTURES)
    return [f for f in all_findings if f["path"].endswith(filename)]


class TestNestedLoops:
    def test_detects_python_nested_loop(self):
        findings = findings_for_file("nested_loops.py")
        kinds = {f["kind"] for f in findings}
        assert "nested-loop" in kinds or "nested-or-callback-loop" in kinds

    def test_detects_js_nested_loop(self):
        findings = findings_for_file("nested_loops.js")
        kinds = {f["kind"] for f in findings}
        assert "nested-loop" in kinds or "nested-or-callback-loop" in kinds


class TestNPlusOne:
    def test_detects_query_in_loop(self):
        findings = findings_for_file("n_plus_one.py")
        kinds = {f["kind"] for f in findings}
        assert "io-or-query-in-loop" in kinds or "n+1-query" in kinds

    def test_detects_generic_verb_on_client_receiver(self):
        # client.get(url) in a loop: generic verb + client-looking receiver
        findings = findings_for_file("n_plus_one.py")
        lines = {f["line"] for f in findings if f["kind"] == "io-or-query-in-loop"}
        assert len(lines) >= 2, f"expected db.query and client.get flagged, got lines {lines}"


class TestMembershipInLoop:
    def test_detects_membership_check(self):
        findings = findings_for_file("membership_in_loop.py")
        kinds = {f["kind"] for f in findings}
        assert "membership-in-loop" in kinds

    def test_set_backed_membership_not_flagged(self):
        # clean_code.py builds a set before the loop; membership on it is O(1)
        findings = findings_for_file("clean_code.py")
        assert not [f for f in findings if f["kind"] == "membership-in-loop"]


class TestSortInLoop:
    def test_detects_sort_in_loop(self):
        findings = findings_for_file("sort_in_loop.py")
        kinds = {f["kind"] for f in findings}
        assert "sort-in-loop" in kinds


class TestRenderPath:
    def test_detects_render_derived_work(self):
        findings = findings_for_file("render_path.tsx")
        kinds = {f["kind"] for f in findings}
        assert "render-derived-work" in kinds


class TestCleanCode:
    def test_no_false_positives(self):
        # includes dict.get() in a loop, set-backed membership, small literal tuple membership
        findings = findings_for_file("clean_code.py")
        assert len(findings) == 0, f"False positives: {findings}"

    def test_no_false_positives_js(self):
        # includes cache.get() and map.delete() inside loops
        findings = findings_for_file("clean_code.js")
        assert len(findings) == 0, f"False positives: {findings}"


class TestOutputFormats:
    def test_json_is_valid(self):
        output = run_scanner(FIXTURES, fmt="json")
        assert isinstance(output, list)
        assert len(output) > 0

    def test_markdown_has_headers(self):
        output = run_scanner(FIXTURES, fmt="markdown")
        assert "# Complexity Hotspots" in output
        assert "## HIGH" in output or "## MEDIUM" in output

    def test_finding_structure(self):
        findings = run_scanner(FIXTURES, fmt="json")
        for f in findings:
            assert "path" in f
            assert "line" in f
            assert "severity" in f
            assert "kind" in f
            assert "message" in f
            assert "suggestion" in f
            assert "confidence" in f


class TestConfidence:
    def test_python_ast_findings_are_high_confidence(self):
        findings = findings_for_file("nested_loops.py")
        assert findings, "expected at least one Python finding"
        assert all(f["confidence"] == "high" for f in findings)

    def test_regex_findings_are_low_confidence(self):
        findings = findings_for_file("nested_loops.js")
        assert findings, "expected at least one JS finding"
        assert all(f["confidence"] == "low" for f in findings)
