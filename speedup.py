"""Speedup of the MPI runs, from the times every job appended.

    python speedup.py

Reads LAB/mpi-times.csv, keeps the fastest run at each rank count, and
prints and plots speedup S = T1 / TN and efficiency E = S / N.
"""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import blackjack as bj  # noqa: E402

PURPLE, GOLD = "#711E7C", "#ECA414"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--times", type=Path, default=bj.LAB / "mpi-times.csv")
    ap.add_argument("--out", type=Path, default=bj.LAB / "speedup.png")
    a = ap.parse_args()

    best = {}
    with open(a.times) as f:
        for r in csv.DictReader(f):
            n, t = int(r["ranks"]), float(r["seconds"])
            best[n] = min(t, best.get(n, t))
    ranks = sorted(best)
    if 1 not in best:
        print("no 1-rank run yet: speedup needs T1")
        return
    t1 = best[1]
    print(f"{'ranks':>5} {'seconds':>8} {'speedup':>8} {'efficiency':>10}")
    for n in ranks:
        s = t1 / best[n]
        print(f"{n:5d} {best[n]:8.1f} {s:8.1f} {s / n:10.0%}")

    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2))
    left.plot(ranks, [best[n] for n in ranks], "o-", color=PURPLE, lw=2)
    left.set_xscale("log", base=2)
    left.set_yscale("log")
    left.set_xlabel("MPI ranks")
    left.set_ylabel("Seconds, all rounds")
    right.plot(ranks, ranks, "--", color="#999999", label="ideal: S = N")
    right.plot(ranks, [t1 / best[n] for n in ranks], "o-", color=GOLD, lw=2,
               label="measured")
    right.set_xlabel("MPI ranks")
    right.set_ylabel("Speedup  T1 / TN")
    right.legend()
    for ax in (left, right):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(a.out, dpi=150)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
