"""Speedup of the MPI and multiprocessing runs, from the times every job appended.

    python speedup.py

Reads LAB/times.csv, keeps the fastest run for each method and number of
workers (MPI ranks or pool workers), and prints and plots speedup
S = T1 / TN and efficiency E = S / N for each method.
"""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import blackjack as bj  # noqa: E402

COLOURS = {"mpi": "#711E7C", "multiprocessing": "#ECA414"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--times", type=Path, default=bj.LAB / "times.csv")
    ap.add_argument("--out", type=Path, default=bj.LAB / "speedup.png")
    a = ap.parse_args()

    best = {}                                   # method -> {workers: fastest seconds}
    with open(a.times) as f:
        for r in csv.DictReader(f):
            n, t = int(r["workers"]), float(r["seconds"])
            runs = best.setdefault(r["method"], {})
            runs[n] = min(t, runs.get(n, t))

    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2))
    print(f"{'method':16s} {'workers':>7} {'seconds':>8} {'speedup':>8} {'efficiency':>10}")
    for method in sorted(best):
        runs = best[method]
        ns = sorted(runs)
        left.plot(ns, [runs[n] for n in ns], "o-", color=COLOURS.get(method), lw=2,
                  label=method)
        if 1 not in runs:
            print(f"{method:16s} no 1-worker run yet: speedup needs T1")
            continue
        for n in ns:
            s = runs[1] / runs[n]
            print(f"{method:16s} {n:7d} {runs[n]:8.1f} {s:8.1f} {s / n:10.0%}")
        right.plot(ns, [runs[1] / runs[n] for n in ns], "o-", color=COLOURS.get(method),
                   lw=2, label=method)
    counts = sorted({n for runs in best.values() for n in runs})
    right.plot(counts, counts, "--", color="#999999", label="ideal: S = N")

    left.set_ylim(bottom=0)
    left.set_ylabel("Seconds, all rounds")
    right.set_ylabel("Speedup  T1 / TN")
    for ax in (left, right):
        ax.set_xscale("log", base=2)
        ax.set_xticks(counts, [str(n) for n in counts])
        ax.minorticks_off()
        ax.set_xlabel("Workers (MPI ranks or pool workers)")
        ax.legend()
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(a.out, dpi=150)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
