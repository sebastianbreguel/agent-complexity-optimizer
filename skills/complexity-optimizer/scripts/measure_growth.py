#!/usr/bin/env python3
"""Measure how a command's run time and peak memory grow with input size, to confirm a complexity claim empirically.

The command gets `{n}` replaced by each size. The fitted exponent k in time ~ n^k gives the order:
about 1 is O(n), 2 is O(n^2), 3 is O(n^3). Process startup is measured with n=0 and subtracted
first, so it doesn't flatten the curve. The repeated runs are resampled (bootstrap) to get a 95%
confidence interval for k, and the verdict is "inconclusive" when that interval spans two classes.

Usage:
  python3 measure_growth.py "python3 bench.py {n}"
  python3 measure_growth.py "node bench.js {n}" --sizes 1000 2000 4000 8000 16000 --repeat 7

Pick sizes so the largest run takes a second or more and the smallest does well over 50 ms of real work.
"""

import argparse
import math
import os
import random
import shlex
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass

DEFAULT_SIZES = [1000, 2000, 4000, 8000]
# Fixed so the shuffled run order and the confidence interval are reproducible.
SEED = 0
BOOTSTRAP_ROUNDS = 1000
# Sizes whose work beyond startup is below these are mostly noise, so they're left out of the fit.
MIN_WORK_SECONDS = 0.05
MIN_WORK_BYTES = 1_000_000
# Below this R², log(time) over log(n) isn't a straight line: the cost isn't one power of n.
MIN_R_SQUARED = 0.9
# Local exponents that rise at every step, and by more than this overall, mean a higher-order term is taking
# over (n^2 + 1000n rises 0.26 over 1000-8000); requiring every step to rise keeps noise from triggering it.
RISING_EXPONENT = 0.2
# Fitted exponent -> what it usually means. n log n fits slightly above 1 on doubling ranges.
GROWTH_CLASSES = [(1.25, "O(n) or O(n log n)"), (1.75, "between O(n log n) and O(n^2)"), (2.5, "O(n^2)"), (math.inf, "O(n^3) or worse")]
# os.wait4 reports the child's peak memory; it doesn't exist on Windows, where only time is measured.
MEASURES_MEMORY = hasattr(os, "wait4")
MAXRSS_UNIT = 1 if sys.platform == "darwin" else 1024  # ru_maxrss is bytes on macOS, kilobytes on Linux


@dataclass
class Run:
    seconds: float
    peak_bytes: int


def run_once(command: str, n: int) -> Run:
    args = shlex.split(command.replace("{n}", str(n)))
    start = time.perf_counter()
    if not MEASURES_MEMORY:
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
        return Run(time.perf_counter() - start, 0)
    process = subprocess.Popen(args, stdout=subprocess.DEVNULL)
    _, status, usage = os.wait4(process.pid, 0)
    seconds = time.perf_counter() - start
    process.returncode = os.waitstatus_to_exitcode(status)
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, args)
    return Run(seconds, usage.ru_maxrss * MAXRSS_UNIT)


def measure(command: str, sizes: list[int], repeat: int, rng: random.Random) -> dict[int, list[Run]]:
    """Run every size once per round in a shuffled order, so slow drift (heat, caches, other load) doesn't line up with n."""
    runs: dict[int, list[Run]] = {n: [] for n in sizes}
    for _ in range(repeat):
        for n in rng.sample(sizes, len(sizes)):
            runs[n].append(run_once(command, n))
    return runs


def fitted_exponent(sizes: list[int], values: list[float]) -> float:
    """Least-squares slope of log(value) over log(n): value ~ n^slope."""
    xs = [math.log(n) for n in sizes]
    ys = [math.log(max(v, 1e-9)) for v in values]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    spread = sum((x - mean_x) ** 2 for x in xs)
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / spread


def r_squared(sizes: list[int], values: list[float], exponent: float) -> float:
    xs = [math.log(n) for n in sizes]
    ys = [math.log(max(v, 1e-9)) for v in values]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    total = sum((y - mean_y) ** 2 for y in ys)
    residual = sum((y - (mean_y + exponent * (x - mean_x))) ** 2 for x, y in zip(xs, ys))
    return 1 - residual / total if total else 1.0


def local_exponents(sizes: list[int], values: list[float]) -> list[float]:
    """Exponent between each pair of consecutive sizes: it rises when a higher-order term is taking over."""
    return [
        math.log(max(b, 1e-9) / max(a, 1e-9)) / math.log(m / n) for (n, a), (m, b) in zip(zip(sizes, values), zip(sizes[1:], values[1:]))
    ]


def exponent_rises(local: list[float]) -> bool:
    return len(local) >= 2 and all(b > a for a, b in zip(local, local[1:])) and local[-1] - local[0] > RISING_EXPONENT


def net_medians(samples: dict[int, list[float]], startup: list[float], floor: float) -> dict[int, float]:
    """Median run per size minus the median startup run, keeping only sizes with enough work to measure.

    The median rather than the fastest run: a bootstrap of the minimum gives intervals that contain the
    true exponent far less than 95% of the time, and less the more repeats there are."""
    base = statistics.median(startup)
    net = {n: statistics.median(values) - base for n, values in samples.items()}
    return {n: value for n, value in net.items() if value >= floor}


def exponent_interval(samples: dict[int, list[float]], startup: list[float], rng: random.Random) -> tuple[float, float] | None:
    """95% interval of the exponent from refits on runs resampled with replacement (bootstrap).

    Rounds where a resampled startup outweighs a size's work have no exponent and are skipped; None when
    that's most of them, because startup noise is then as large as the work being measured."""
    sizes = sorted(samples)
    slopes = []
    for _ in range(BOOTSTRAP_ROUNDS):
        base = statistics.median(rng.choices(startup, k=len(startup)))
        values = [statistics.median(rng.choices(samples[n], k=len(samples[n]))) - base for n in sizes]
        if min(values) > 0:
            slopes.append(fitted_exponent(sizes, values))
    if len(slopes) < BOOTSTRAP_ROUNDS // 2:
        return None
    slopes.sort()
    return slopes[int(0.025 * len(slopes))], slopes[int(0.975 * len(slopes)) - 1]


def growth_class(exponent: float) -> str:
    return next(label for limit, label in GROWTH_CLASSES if exponent < limit)


def verdict(low: float, high: float) -> str:
    low_class, high_class = growth_class(low), growth_class(high)
    return low_class if low_class == high_class else f"inconclusive, anywhere from {low_class} to {high_class}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate the growth order of a command from timed runs.")
    parser.add_argument("command", help='Command with {n} for the input size, e.g. "python3 bench.py {n}".')
    parser.add_argument("--sizes", type=int, nargs="+", default=DEFAULT_SIZES)
    parser.add_argument("--repeat", type=int, default=5, help="Runs per size; the median counts, all of them feed the interval.")
    parser.add_argument(
        "--startup-n", type=int, default=0, help="Size that measures process startup, subtracted from the others (1 if 0 is invalid)."
    )
    args = parser.parse_args()
    if "{n}" not in args.command:
        parser.error("the command must contain {n}")
    sizes = sorted(set(args.sizes) - {args.startup_n})
    if len(sizes) < 2 or sizes[0] <= 0:
        parser.error("need at least two different positive sizes besides --startup-n")

    try:
        run_once(args.command, args.startup_n)  # warm-up run (disk cache, compiled caches), not recorded
    except subprocess.CalledProcessError:
        parser.error(f"the command fails at n={args.startup_n}; pass --startup-n with a size it accepts, e.g. --startup-n 1")
    rng = random.Random(SEED)
    print(f"Running {len(sizes)} sizes plus startup (n={args.startup_n}), {args.repeat} rounds in shuffled order...\n")
    runs = measure(args.command, [args.startup_n, *sizes], args.repeat, rng)
    seconds = {n: [run.seconds for run in runs[n]] for n in sizes}
    peaks = {n: [float(run.peak_bytes) for run in runs[n]] for n in sizes}
    startup_seconds = [run.seconds for run in runs[args.startup_n]]
    startup_peaks = [float(run.peak_bytes) for run in runs[args.startup_n]]

    work = net_medians(seconds, startup_seconds, MIN_WORK_SECONDS)
    fit_sizes = sorted(work)
    fit_values = [work[n] for n in fit_sizes]
    local = local_exponents(fit_sizes, fit_values)
    local_by_size = dict(zip(fit_sizes[1:], local))

    print(f"{'n':>10} {'seconds':>10} {'peak MB':>9} {'local exp':>10}")
    for n in sizes:
        peak = f"{statistics.median(peaks[n]) / 1e6:.1f}" if MEASURES_MEMORY else "—"
        step = f"{local_by_size[n]:.2f}" if n in local_by_size else "—"
        print(f"{n:>10} {statistics.median(seconds[n]):>10.4f} {peak:>9} {step:>10}")
    startup_memory = f" and {statistics.median(startup_peaks) / 1e6:.1f} MB" if MEASURES_MEMORY else ""
    print(f"\nStartup (n={args.startup_n}): {statistics.median(startup_seconds):.4f} s{startup_memory}, subtracted before fitting.")

    if len(work) < 2:
        print(f"Inconclusive: fewer than 2 sizes did over {MIN_WORK_SECONDS * 1000:.0f} ms of work beyond startup. Use larger sizes.")
    else:
        exponent = fitted_exponent(fit_sizes, fit_values)
        interval = exponent_interval({n: seconds[n] for n in fit_sizes}, startup_seconds, rng)
        # Two points always fit a straight line, so R² only says something from three sizes on.
        fit = r_squared(fit_sizes, fit_values, exponent) if len(fit_sizes) > 2 else None
        if interval is None:
            print(f"Time exponent: {exponent:.2f} -> inconclusive: startup time varies as much as the work. Use larger sizes.")
        else:
            low, high = interval
            fit_note = f"R² {fit:.2f}" if fit is not None else "R² n/a with 2 sizes"
            print(
                f"Time exponent: {exponent:.2f} (95% CI {low:.2f} to {high:.2f}, {fit_note}) -> {verdict(low, high)}"
                f" (from {len(fit_sizes)} of {len(sizes)} sizes)"
            )
        if fit is not None and fit < MIN_R_SQUARED:
            print(f"  R² under {MIN_R_SQUARED}: the cost isn't a single power of n, so read the local exponents per size.")
        if exponent_rises(local):
            print(
                f"  The local exponent rises with n ({local[0]:.2f} -> {local[-1]:.2f}): a higher-order term takes over"
                " at larger sizes, so the real order is at least the last value."
            )

    if MEASURES_MEMORY:
        memory = net_medians(peaks, startup_peaks, MIN_WORK_BYTES)
        if len(memory) < 2:
            print(f"Memory: under {MIN_WORK_BYTES / 1e6:.0f} MB above startup at most sizes, too little to fit.")
        else:
            memory_sizes = sorted(memory)
            memory_exponent = fitted_exponent(memory_sizes, [memory[n] for n in memory_sizes])
            print(f"Memory exponent: {memory_exponent:.2f} -> {growth_class(memory_exponent)} (peak RSS above startup)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
