"""One row of one round: what each array task runs.

Reads the round's table, simulates hit and stand in the row's 10 cells and
writes round-<N>/row-<NN>.csv in the shared folder. No task talks to another.

    python slurm/row.py --row 12 --round 1
"""

import argparse
from pathlib import Path

import blackjack as bj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", type=int, required=True, help="0-26")
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--hands", type=int, default=2_000_000, help="hands per action")
    ap.add_argument("--table", type=Path, help="default: LAB/table-round-ROUND.csv")
    ap.add_argument("--out", type=Path, help="default: LAB/round-ROUND/")
    a = ap.parse_args()

    table = bj.read_table(a.table or bj.LAB / f"table-round-{a.round}.csv")
    out = a.out or bj.LAB / f"round-{a.round}"
    out.mkdir(parents=True, exist_ok=True)
    cells = range(10 * a.row, 10 * a.row + 10)
    bj.write_results([bj.simulate_cell(c, table, a.hands) for c in cells],
                     out / f"row-{a.row:02d}.csv")
    print(f"round {a.round}: wrote {out / f'row-{a.row:02d}.csv'}")


if __name__ == "__main__":
    main()
