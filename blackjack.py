"""Blackjack by simulation: the shared code for the Module 8 lab.

Rules
-----
- Infinite deck: every card is drawn with replacement. Cards 2 to 9 count
  their value, 10, J, Q and K count 10, and an ace counts 11 or 1
- You choose only hit or stand
- The dealer draws until 17 or more and stands on soft 17
- A dealer blackjack (21 in two cards) beats every other hand

The strategy table has 27 rows, one per hand (hard 4 to 21, soft 13 to 21),
and 10 columns, one per dealer upcard (2 to 10, and ace). Its 270 cells are
numbered row by row: cell 0 is hard 4 against a 2, cell 10 is hard 5 against
a 2. A cell holds 1 for hit and 0 for stand.

Each cell's random numbers depend only on the cell, so the same table and the
same number of hands give the same answer however the cells are split up: one
Slurm task per row, or any number of MPI ranks.

    python blackjack.py cell --hand H16 --up 7 --hands 100000
    python blackjack.py row --row 12 --round 1 --hands 400000 --out round-1/
"""

import argparse
import csv
import os
from pathlib import Path

import numpy as np

CARDS = np.array([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11])  # 11 is an ace
UPCARDS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
UPCARD_NAMES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "A"]
ROWS = [(False, t) for t in range(4, 22)] + [(True, t) for t in range(13, 22)]
HAND_NAMES = [f"{'S' if soft else 'H'}{total}" for soft, total in ROWS]
SEED = 56430
HERE = Path(__file__).resolve().parent

# The shared folder: each round's table and results, and the MPI times. On
# Midway3 it is the class folder; elsewhere, set BLACKJACK_LAB to any folder.
LAB = Path(os.environ.get("BLACKJACK_LAB", "/project/mpcs56430/2026-autumn/blackjack"))


def starting_table():
    """The shared folder's table-round-1.csv, or this folder's copy."""
    shared = LAB / "table-round-1.csv"
    return shared if shared.exists() else HERE / "table-round-1.csv"


# ------------------------------------------------------------- the game

def draw(rng, n):
    """n cards from an infinite deck."""
    return CARDS[rng.integers(0, 13, n)]


def add_card(total, soft, card):
    """Add one card to many hands at once. A hand is (total, soft)."""
    ace = card == 11
    big = ace & (total + 11 <= 21)               # the ace can count 11
    total = total + np.where(ace, np.where(big, 11, 1), card)
    soft = soft | big
    over = (total > 21) & soft                   # count a soft ace as 1 instead
    return np.where(over, total - 10, total), soft & ~over


def dealer(rng, up, n):
    """The dealer's final totals (22 means bust) and who has blackjack."""
    total = np.full(n, up)
    soft = np.full(n, up == 11)
    total, soft = add_card(total, soft, draw(rng, n))
    blackjack = total == 21
    live = total < 17
    while live.any():
        t, s = add_card(total[live], soft[live], draw(rng, live.sum()))
        total[live], soft[live] = t, s
        live = total < 17
    return np.minimum(total, 22), blackjack


def play_on(rng, total, soft, col, table):
    """Keep hitting by the table until each hand stands or busts."""
    total, soft = total.copy(), soft.copy()
    live = total <= 21
    while True:
        row = np.where(soft, 18 + np.clip(total - 13, 0, 8), np.clip(total - 4, 0, 17))
        wants = np.where(soft & (total == 12), 1, table[row, col])   # soft 12: hit
        hit = live & (wants == 1)
        if not hit.any():
            return total, soft
        t, s = add_card(total[hit], soft[hit], draw(rng, hit.sum()))
        total[hit], soft[hit] = t, s
        live = total <= 21


def settle(player, dealer_total, dealer_blackjack):
    """+1 for a win, 0 for a push, -1 for a loss."""
    win = (player <= 21) & ((dealer_total > 21) | (player > dealer_total))
    lose = (player > 21) | ((dealer_total <= 21) & (player < dealer_total)) | dealer_blackjack
    return np.where(lose, -1.0, np.where(win, 1.0, 0.0))


def play(soft, total, up, action, table, hands, rng):
    """Mean result per hand of one action in one cell, and its standard error.

    "hit" takes one card, then follows the table. "stand" stands now.
    """
    t = np.full(hands, total)
    s = np.full(hands, soft)
    if action == "hit":
        t, s = add_card(t, s, draw(rng, hands))
        t, s = play_on(rng, t, s, UPCARDS.index(up), table)
    d, bj = dealer(rng, up, hands)
    r = settle(t, d, bj)
    return r.mean(), r.std(ddof=1) / np.sqrt(hands)


def simulate_cell(cell, table, hands):
    """Hit and stand in one cell: a dict ready to write as a CSV row."""
    soft, total = ROWS[cell // 10]
    up = UPCARDS[cell % 10]
    stand, stand_se = play(soft, total, up, "stand", table, hands,
                           np.random.default_rng([SEED, cell, 0]))
    hit, hit_se = play(soft, total, up, "hit", table, hands,
                       np.random.default_rng([SEED, cell, 1]))
    return {"cell": cell, "hand": HAND_NAMES[cell // 10], "up": UPCARD_NAMES[cell % 10],
            "hands": hands, "stand": round(stand, 6), "stand_se": round(stand_se, 6),
            "hit": round(hit, 6), "hit_se": round(hit_se, 6)}


# ------------------------------------------------------------- files

FIELDS = ["cell", "hand", "up", "hands", "stand", "stand_se", "hit", "hit_se"]


def read_table(path):
    """A table CSV (hand,2,...,10,A with H or S) as a 27 x 10 array of 1/0."""
    with open(path) as f:
        rows = {r["hand"]: r for r in csv.DictReader(f)}
    return np.array([[1 if rows[h][u] == "H" else 0 for u in UPCARD_NAMES]
                     for h in HAND_NAMES], dtype=np.int8)


def write_table(table, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hand"] + UPCARD_NAMES)
        for name, row in zip(HAND_NAMES, table):
            w.writerow([name] + ["H" if v else "S" for v in row])


def write_results(results, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(results)


def next_table(table, results):
    """Switch every simulated cell to the better action. Returns the new
    table and the list of cells that changed."""
    new = table.copy()
    for r in results:
        new[r["cell"] // 10, r["cell"] % 10] = 1 if r["hit"] > r["stand"] else 0
    flipped = [int(c) for c in np.flatnonzero(new.ravel() != table.ravel())]
    return new, flipped


def show(table):
    """Print a table as H and S."""
    print("      " + " ".join(f"{u:>2}" for u in UPCARD_NAMES))
    for name, row in zip(HAND_NAMES, table):
        print(f"{name:6s}" + " ".join(f"{'H' if v else 'S':>2}" for v in row))


# ------------------------------------------------------------- command line

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)

    one = sub.add_parser("cell", help="hit and stand in one cell, printed")
    one.add_argument("--hand", required=True, help="for example H16 or S17")
    one.add_argument("--up", required=True, help="dealer upcard: 2-10 or A")
    one.add_argument("--hands", type=int, default=100_000, help="hands per action")
    one.add_argument("--table", type=Path, default=None,
                     help="table to follow after a hit (default: the starting table)")

    row = sub.add_parser("row", help="one row of cells, written to a CSV")
    row.add_argument("--row", type=int, required=True, help="0-26")
    row.add_argument("--round", type=int, required=True)
    row.add_argument("--hands", type=int, default=400_000, help="hands per action")
    row.add_argument("--table", type=Path, help="default: LAB/table-round-ROUND.csv")
    row.add_argument("--out", type=Path, help="default: LAB/round-ROUND/")

    a = ap.parse_args()
    if a.command == "cell":
        table = a.table or starting_table()
        cell = 10 * HAND_NAMES.index(a.hand.upper()) + UPCARD_NAMES.index(a.up.upper())
        r = simulate_cell(cell, read_table(table), a.hands)
        gap = r["hit"] - r["stand"]
        two_se = 2 * (r["hit_se"] ** 2 + r["stand_se"] ** 2) ** 0.5
        if abs(gap) < two_se:
            verdict = "too close to call"
        else:
            verdict = ("hit" if gap > 0 else "stand") + " is better"
        print(f"{r['hand']} vs {r['up']}, {a.hands:,} hands each "
              f"(after a hit, follow {table.name})")
        print(f"  stand {r['stand']:+.4f} ± {r['stand_se']:.4f}")
        print(f"  hit   {r['hit']:+.4f} ± {r['hit_se']:.4f}")
        print(f"  hit minus stand {gap:+.4f}, twice its ± {two_se:.4f}: {verdict}")
    else:
        table = read_table(a.table or LAB / f"table-round-{a.round}.csv")
        out = a.out or LAB / f"round-{a.round}"
        out.mkdir(parents=True, exist_ok=True)
        results = [simulate_cell(c, table, a.hands) for c in range(10 * a.row, 10 * a.row + 10)]
        write_results(results, out / f"row-{a.row:02d}.csv")
        print(f"round {a.round}: wrote {out / f'row-{a.row:02d}.csv'}")


if __name__ == "__main__":
    main()
