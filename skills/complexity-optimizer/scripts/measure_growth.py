#!/usr/bin/env python3
"""Measure how a command's run time grows with input size, to confirm a complexity claim empirically.

The command gets `{n}` replaced by each size. Doubling n and watching the time tells the order:
x2 time means O(n), x4 means O(n^2), x8 means O(n^3). The fitted exponent summarizes all sizes.

Usage:
  python3 measure_growth.py "python3 bench.py {n}"
  python3 measure_growth.py "node bench.js {n}" --sizes 1000 2000 4000 8000 16000 --repeat 5

Pick sizes where the smallest run takes at least ~50 ms, so process startup doesn't dominate.
"""

import argparse
import math
import shlex
import subprocess
import sys
import time

DEFAULT_SIZES = [1000, 2000, 4000, 8000]
STARTUP_DOMINATED_SECONDS = 0.05
# Fitted exponent -> what it usually means. n log n fits slightly above 1 on doubling ranges.
GROWTH_CLASSES = [(1.25, "O(n) or O(n log n)"), (1.75, "between O(n log n) and O(n^2)"), (2.5, "O(n^2)"), (math.inf, "O(n^3) or worse")]


def time_command(command: str, n: int, repeat: int) -> float:
    """Best of `repeat` wall-clock runs: the minimum is the least noisy estimate of the real cost."""
    args = shlex.split(command.replace("{n}", str(n)))
    best = math.inf
    for _ in range(repeat):
        start = time.perf_counter()
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
        best = min(best, time.perf_counter() - start)
    return best


def fitted_exponent(sizes: list[int], seconds: list[float]) -> float:
    """Least-squares slope of log(time) over log(n): time ~ n^slope."""
    xs = [math.log(n) for n in sizes]
    ys = [math.log(max(t, 1e-9)) for t in seconds]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    spread = sum((x - mean_x) ** 2 for x in xs)
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / spread


def growth_class(exponent: float) -> str:
    return next(label for limit, label in GROWTH_CLASSES if exponent < limit)


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate the growth order of a command from timed runs.")
    parser.add_argument("command", help='Command with {n} for the input size, e.g. "python3 bench.py {n}".')
    parser.add_argument("--sizes", type=int, nargs="+", default=DEFAULT_SIZES)
    parser.add_argument("--repeat", type=int, default=3, help="Runs per size; the fastest one counts.")
    args = parser.parse_args()
    if "{n}" not in args.command:
        parser.error("the command must contain {n}")
    if len(set(args.sizes)) < 2:
        parser.error("need at least two different sizes")

    sizes = sorted(set(args.sizes))
    seconds = []
    print(f"{'n':>10} {'seconds':>10} {'x prev':>8}")
    for n in sizes:
        seconds.append(time_command(args.command, n, args.repeat))
        ratio = f"{seconds[-1] / seconds[-2]:.2f}" if len(seconds) > 1 and seconds[-2] > 0 else "—"
        print(f"{n:>10} {seconds[-1]:>10.4f} {ratio:>8}")

    # Runs dominated by process startup flatten the curve, so they are left out of the fit. With
    # fewer than two real measurements there is no verdict: a flat curve would wrongly say O(n).
    measured = [(n, t) for n, t in zip(sizes, seconds) if t >= STARTUP_DOMINATED_SECONDS]
    if len(measured) < 2:
        print(f"\nInconclusive: fewer than 2 runs took over {STARTUP_DOMINATED_SECONDS * 1000:.0f} ms (mostly startup). Use larger sizes.")
        return 0
    exponent = fitted_exponent([n for n, _ in measured], [t for _, t in measured])
    print(f"\nFitted exponent: {exponent:.2f} -> {growth_class(exponent)} (from {len(measured)} of {len(sizes)} sizes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
