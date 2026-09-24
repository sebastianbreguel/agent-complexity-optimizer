import subprocess
import sys
from pathlib import Path

from measure_growth import fitted_exponent, growth_class

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "complexity-optimizer" / "scripts" / "measure_growth.py"


def test_fitted_exponent_recovers_known_orders():
    sizes = [1000, 2000, 4000, 8000]
    assert round(fitted_exponent(sizes, [n * 1e-6 for n in sizes]), 2) == 1.0
    assert round(fitted_exponent(sizes, [n * n * 1e-9 for n in sizes]), 2) == 2.0


def test_growth_class_labels():
    assert growth_class(1.05) == "O(n) or O(n log n)"
    assert growth_class(2.0) == "O(n^2)"
    assert growth_class(3.1) == "O(n^3) or worse"


def test_command_requires_placeholder():
    result = subprocess.run([sys.executable, str(SCRIPT), "echo hi"], capture_output=True, text=True)
    assert result.returncode == 2
    assert "{n}" in result.stderr


def test_short_runs_are_inconclusive():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), f"{sys.executable} -c pass {{n}}", "--sizes", "1", "2", "--repeat", "1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Inconclusive" in result.stdout
    assert "O(n)" not in result.stdout
