"""Collect one round of results and make the next table.

Reads every row-NN.csv in the round's folder, switches each cell to the
better action, and writes:

  table-round-<N+1>.csv   the table the next round follows
  round-<N>.png           heat map: hit minus stand in each cell, the action,
                          cells that flipped this round (gold outline) and
                          cells too close to call (hatched)

Rows still missing are listed, so they can be run again. It can be run while
a round is still coming in: missing cells show as dots.

    python assemble.py --round 1
"""

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

import blackjack as bj  # noqa: E402

GOLD = "#ECA414"


def read_results(folder):
    """Every cell in the round's row files. If a cell was run more than once,
    keep the run with the most hands."""
    cells = {}
    for p in sorted(Path(folder).glob("row-*.csv")):
        with open(p) as f:
            for r in csv.DictReader(f):
                r = {k: (float(v) if k in ("stand", "stand_se", "hit", "hit_se") else v)
                     for k, v in r.items()}
                r["cell"], r["hands"] = int(r["cell"]), int(r["hands"])
                if r["cell"] not in cells or r["hands"] > cells[r["cell"]]["hands"]:
                    cells[r["cell"]] = r
    return cells


def heat_map(table, cells, flipped, disputed, differs, title, path):
    margin = np.full((27, 10), np.nan)
    for c, r in cells.items():
        margin[c // 10, c % 10] = r["hit"] - r["stand"]
    fig, ax = plt.subplots(figsize=(8, 11))
    lim = np.nanmax(np.abs(margin)) if np.isfinite(margin).any() else 1
    im = ax.imshow(margin, cmap="PuOr_r", norm=TwoSlopeNorm(0, -lim, lim), aspect="auto")
    bar = fig.colorbar(im, ax=ax, shrink=0.5, pad=0.03)
    bar.set_label("hit minus stand, per hand\n(orange: hit better, purple: stand better)")
    ax.text(0, -0.08, "gold outline: flipped this round   hatched: within 2 SE"
            + ("   red outline: differs from basic strategy" if differs else ""),
            transform=ax.transAxes, fontsize=8)
    for c in range(270):
        i, j = c // 10, c % 10
        if c not in cells:
            ax.text(j, i, "·", ha="center", va="center", color="#999999")
            continue
        ax.text(j, i, "H" if table[i, j] else "S", ha="center", va="center",
                fontsize=11, weight="bold")
        if c in disputed:
            ax.add_patch(Rectangle((j - .5, i - .5), 1, 1, fill=False, hatch="///",
                                   ec="#555555", lw=0))
        if c in flipped:
            ax.add_patch(Rectangle((j - .45, i - .45), .9, .9, fill=False, ec=GOLD, lw=3))
        if c in differs:
            ax.add_patch(Rectangle((j - .45, i - .45), .9, .9, fill=False, ec="red", lw=3))
    ax.set_xticks(range(10), bj.UPCARD_NAMES)
    ax.set_yticks(range(27), bj.HAND_NAMES)
    ax.xaxis.tick_top()
    ax.set_xlabel("Dealer upcard")
    ax.xaxis.set_label_position("top")
    ax.axhline(17.5, color="black", lw=1.5)
    ax.set_title(title, pad=40, fontsize=14, weight="bold")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def ranges(numbers):
    """[3, 4, 5, 9] -> "3-5,9", the form --array takes."""
    out, start = [], numbers[0]
    for prev, n in zip(numbers, numbers[1:] + [None]):
        if n != prev + 1:
            out.append(f"{start}-{prev}" if prev > start else f"{start}")
            start = n
    return ",".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--lab", type=Path, default=bj.LAB,
                    help="folder with table-round-N.csv and round-N/")
    ap.add_argument("--compare", type=Path, help="a table to outline differences from")
    a = ap.parse_args()

    old = bj.read_table(a.lab / f"table-round-{a.round}.csv")
    cells = read_results(a.lab / f"round-{a.round}")
    new, flipped = bj.next_table(old, list(cells.values()))
    disputed = {c for c, r in cells.items()
                if abs(r["hit"] - r["stand"]) < 2 * np.hypot(r["hit_se"], r["stand_se"])}
    differs = set()
    if a.compare:
        ref = bj.read_table(a.compare)
        differs = {int(c) for c in np.flatnonzero(new.ravel() != ref.ravel())}

    title = (f"Round {a.round}: {len(cells)} of 270 cells, {len(flipped)} flipped, "
             f"{len(disputed)} too close to call")
    heat_map(new, cells, set(flipped), disputed, differs, title,
             a.lab / f"round-{a.round}.png")
    print(title)
    print(f"wrote {a.lab / f'round-{a.round}.png'}")

    missing = sorted({c // 10 for c in range(270) if c not in cells})
    if missing:
        rows = ranges(missing)
        print(f"missing rows {rows}: rerun with  sbatch --array={rows} "
              f"--export=ALL,ROUND={a.round} array_round.sbatch")
        sys.exit(1)              # a failed step, so a job chain stops here
    bj.write_table(new, a.lab / f"table-round-{a.round + 1}.csv")
    print(f"wrote {a.lab / f'table-round-{a.round + 1}.csv'}")
    for c in flipped:
        print(f"  flipped {bj.HAND_NAMES[c // 10]} vs {bj.UPCARD_NAMES[c % 10]}: "
              f"now {'hit' if new.ravel()[c] else 'stand'}")
    if not flipped:
        print("nothing flipped: the table has settled")
    if a.compare:
        print("differs from the comparison table:",
              [f"{bj.HAND_NAMES[c // 10]} vs {bj.UPCARD_NAMES[c % 10]}" for c in sorted(differs)]
              or "none")


if __name__ == "__main__":
    main()
