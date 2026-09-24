import random
import re
import subprocess
import sys
from pathlib import Path

import pytest
from measure_growth import (
    MEASURES_MEMORY,
    exponent_interval,
    exponent_rises,
    fitted_exponent,
    growth_class,
    local_exponents,
    net_minimums,
    verdict,
)

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "complexity-optimizer" / "scripts" / "measure_growth.py"
SIZES = [1000, 2000, 4000, 8000]


def run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def test_fitted_exponent_recovers_known_orders():
    assert round(fitted_exponent(SIZES, [n * 1e-6 for n in SIZES]), 2) == 1.0
    assert round(fitted_exponent(SIZES, [n * n * 1e-9 for n in SIZES]), 2) == 2.0


def test_growth_class_labels():
    assert growth_class(1.05) == "O(n) or O(n log n)"
    assert growth_class(2.0) == "O(n^2)"
    assert growth_class(3.1) == "O(n^3) or worse"


def test_startup_is_subtracted_before_fitting():
    startup = 0.5
    samples = {n: [startup + n * 1e-4] for n in SIZES}
    work = net_minimums(samples, [startup], 0.05)
    assert round(fitted_exponent(sorted(work), [work[n] for n in sorted(work)]), 2) == 1.0
    assert fitted_exponent(SIZES, [samples[n][0] for n in SIZES]) < 0.7  # what startup does to an O(n) curve


def test_interval_brackets_the_true_exponent():
    noise = [1.0, 1.04, 1.02, 1.07, 1.01]
    samples = {n: [n * n * 1e-8 * factor for factor in noise] for n in SIZES}
    low, high = exponent_interval(samples, [0.0] * len(noise), random.Random(0))
    assert low <= 2.0 <= high
    assert high - low < 0.2


def test_verdict_is_inconclusive_across_classes():
    assert verdict(1.9, 2.1) == "O(n^2)"
    assert verdict(1.1, 1.4).startswith("inconclusive")


def test_rising_local_exponent_reveals_a_hidden_quadratic():
    hidden = [n * n + 1000.0 * n for n in SIZES]
    assert fitted_exponent(SIZES, hidden) < 1.75  # the single fit alone would say "below O(n^2)"
    assert exponent_rises(local_exponents(SIZES, hidden))
    assert not exponent_rises(local_exponents(SIZES, [float(n * n) for n in SIZES]))


def test_command_requires_placeholder():
    result = run_script("echo hi")
    assert result.returncode == 2
    assert "{n}" in result.stderr


def test_short_runs_are_inconclusive():
    result = run_script(f"{sys.executable} -c pass {{n}}", "--sizes", "1", "2", "--repeat", "1")
    assert result.returncode == 0
    assert "Inconclusive" in result.stdout
    assert "O(n)" not in result.stdout


@pytest.mark.skipif(not MEASURES_MEMORY, reason="peak memory needs os.wait4")
def test_memory_exponent_of_quadratic_allocation():
    command = f"{sys.executable} -c \"import sys; b = b'x' * (int(sys.argv[1]) ** 2)\" {{n}}"
    result = run_script(command, "--sizes", "2000", "4000", "8000", "--repeat", "1")
    match = re.search(r"Memory exponent: (\d+\.\d+)", result.stdout)
    assert match, result.stdout
    assert abs(float(match.group(1)) - 2.0) < 0.2
