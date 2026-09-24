import subprocess
import sys
from pathlib import Path

from verdicts import prior_adjusted_precision, status, wilson_interval

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "complexity-optimizer" / "scripts" / "verdicts.py"


def run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def test_wilson_interval_on_thirty_verdicts():
    assert wilson_interval(26, 30)[0] >= 0.7  # 26/30 real: precision is at least 0.7
    assert wilson_interval(9, 30)[1] < 0.5  # 9/30 real: precision is below 0.5


def test_status_follows_the_not_useful_rate():
    assert status(0, 5).startswith("needs data")
    assert status(0, 20) == "active"
    assert status(6, 20) == "probation"
    assert status(12, 20) == "off"


def test_prior_fades_as_verdicts_arrive():
    assert prior_adjusted_precision(0, 0, "ast") == 0.8
    assert prior_adjusted_precision(30, 30, "ast") == 0.95


def test_latest_verdict_per_fingerprint_counts(tmp_path: Path):
    file = str(tmp_path / "verdicts" / "shop.jsonl")  # the folder doesn't exist yet
    for fingerprint, verdict in [
        ("src/a.py::load::nested-loop", "confirmed"),
        ("src/a.py::load::nested-loop", "false_positive"),
        ("src/b.ts::render::nested-loop", "fixed"),
    ]:
        assert run_script("add", file, fingerprint, verdict).returncode == 0
    table = run_script("report", file).stdout
    assert "| nested-loop | .py | 1 | 0 |" in table
    assert "| nested-loop | .ts | 1 | 1 |" in table


def test_add_rejects_an_unknown_rule(tmp_path: Path):
    result = run_script("add", str(tmp_path / "v.jsonl"), "src/a.py::load::slow-thing", "confirmed")
    assert result.returncode == 2
    assert not (tmp_path / "v.jsonl").exists()


def test_report_on_a_missing_file_is_a_usage_error(tmp_path: Path):
    result = run_script("report", str(tmp_path / "none.jsonl"))
    assert result.returncode == 2
    assert "none.jsonl" in result.stderr
