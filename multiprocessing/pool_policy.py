"""Every round of policy iteration in one Python program with a pool of workers.

The same rounds as mpi/mpi_policy.py, on one node. The main process holds
the table and starts N worker processes. Then, each round:

  1. map     send every worker the current table and its share of the cells
  2. work    each worker simulates its share of the 270 cells
  3. return  map hands back every worker's results, in order
  4. update  the main process switches each cell to the better action

The job stops when a round changes nothing. Worker w takes cells w, w + N,
w + 2N, ..., the same split as MPI rank w, so the two programs do the same
work and only the way they run differs.

    python multiprocessing/pool_policy.py --workers 4
"""

import argparse
import time
from multiprocessing import Pool
from pathlib import Path

import blackjack as bj


def simulate_share(job):
    """One worker's share of a round. Runs in a worker process."""
    worker, workers, table, hands = job
    return [bj.simulate_cell(c, table, hands) for c in range(worker, 270, workers)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4, help="worker processes")
    ap.add_argument("--hands", type=int, default=2_000_000, help="hands per action")
    ap.add_argument("--table", type=Path, default=None,
                    help="starting table (default: table-round-1.csv)")
    ap.add_argument("--max-rounds", type=int, default=10)
    ap.add_argument("--out", type=Path, help="write the final table here")
    ap.add_argument("--times", type=Path, help="append this run's time to a CSV")
    a = ap.parse_args()

    table = bj.read_table(a.table or bj.starting_table())
    with Pool(a.workers) as pool:                       # start the worker processes
        start = time.perf_counter()
        for rnd in range(1, a.max_rounds + 1):
            t0 = time.perf_counter()
            jobs = [(w, a.workers, table, a.hands) for w in range(a.workers)]
            shares = pool.map(simulate_share, jobs)                          # 1, 2, 3
            results = [r for share in shares for r in share]
            table, flipped = bj.next_table(table, results)                   # 4
            print(f"round {rnd}: {len(flipped):3d} cells flipped "
                  f"({time.perf_counter() - t0:6.1f} s)", flush=True)
            if not flipped:
                break
        elapsed = time.perf_counter() - start

    workers = f"{a.workers} worker" + ("s" if a.workers > 1 else "")
    print(f"\n{workers}, {rnd} round{'s' if rnd > 1 else ''}, {a.hands:,} hands per action: {elapsed:.1f} s\n")
    bj.show(table)
    if a.out:
        bj.write_table(table, a.out)
    if a.times:
        bj.record_time(a.times, "multiprocessing", a.workers, elapsed, rnd, a.hands)


if __name__ == "__main__":
    main()
