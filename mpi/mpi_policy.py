"""Every round of policy iteration in one MPI job.

Every rank runs this same program. Rank 0 reads the starting table; then,
each round:

  1. bcast   rank 0 sends the current table to every rank
  2. work    each rank simulates its share of the 270 cells
  3. gather  rank 0 collects every rank's results
  4. update  rank 0 switches each cell to the better action
  5. bcast   rank 0 tells every rank whether anything changed

The job stops when a round changes nothing. Run it with mpiexec:

    mpiexec -n 4 python mpi/mpi_policy.py
"""

import argparse
from pathlib import Path

from mpi4py import MPI

import blackjack as bj

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hands", type=int, default=2_000_000, help="hands per action")
    ap.add_argument("--table", type=Path, default=None,
                    help="starting table (default: table-round-1.csv)")
    ap.add_argument("--max-rounds", type=int, default=10)
    ap.add_argument("--out", type=Path, help="write the final table here")
    ap.add_argument("--times", type=Path, help="append this run's time to a CSV")
    a = ap.parse_args()

    table = bj.read_table(a.table or bj.starting_table()) if rank == 0 else None
    my_cells = range(rank, 270, size)          # rank 0: 0, size, 2*size, ...
    comm.Barrier()
    start = MPI.Wtime()

    for rnd in range(1, a.max_rounds + 1):
        t0 = MPI.Wtime()
        table = comm.bcast(table, root=0)                                    # 1
        mine = [bj.simulate_cell(c, table, a.hands) for c in my_cells]       # 2
        everyone = comm.gather(mine, root=0)                                 # 3
        if rank == 0:                                                        # 4
            results = [r for part in everyone for r in part]
            table, flipped = bj.next_table(table, results)
            print(f"round {rnd}: {len(flipped):3d} cells flipped "
                  f"({MPI.Wtime() - t0:6.1f} s)", flush=True)
            done = not flipped
        else:
            done = None
        if comm.bcast(done, root=0):                                         # 5
            break

    elapsed = MPI.Wtime() - start
    if rank == 0:
        ranks = f"{size} rank" + ("s" if size > 1 else "")
        print(f"\n{ranks}, {rnd} round{'s' if rnd > 1 else ''}, {a.hands:,} hands per action: {elapsed:.1f} s\n")
        bj.show(table)
        if a.out:
            bj.write_table(table, a.out)
        if a.times:
            bj.record_time(a.times, "mpi", size, elapsed, rnd, a.hands)


if __name__ == "__main__":
    main()
