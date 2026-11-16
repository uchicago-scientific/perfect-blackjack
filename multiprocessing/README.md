# multiprocessing: every round in one program

One job runs every round, as one ordinary Python program. `Pool(N)` from
Python's standard `multiprocessing` module starts N worker processes on the
same node. The main process holds the table; each round, `pool.map` sends
every worker the table and its share of the cells, and returns their results
in order. No MPI library and no `mpiexec`, but every worker must be on the
same node as the main process.

Run every command from the repository's top folder (`~/blackjack`), where
`logs/` is.

| File | What it does |
|---|---|
| `pool_policy.py` | Every round of policy iteration in one program with a pool of workers |
| `pool.sbatch` | Runs `pool_policy.py` as a job with any number of workers |

## Every round in one job

```
sbatch --cpus-per-task=8 multiprocessing/pool.sbatch    # 8 workers on one node
squeue -u $USER
cat logs/bj-pool-<job id>.out
```

`--cpus-per-task` is the number of workers: the job is one task, one process,
with that many CPUs. Each round:

1. `pool.map` sends every worker the current table and its share of the 270
   cells: worker *w* takes cells *w*, *w* + N, *w* + 2N, ...
2. each worker simulates its share
3. `pool.map` returns every worker's results to the main process, in order
4. the main process switches each cell to the better action

It stops when a round changes nothing. The log shows each round, the total
time and the final table:

```
round 1:  41 cells flipped (  35.4 s)
round 2:   5 cells flipped (  33.4 s)
round 3:   0 cells flipped (  29.8 s)

8 workers, 3 rounds, 2,000,000 hands per action: 98.5 s

       2  3  4  5  6  7  8  9 10  A
H4     H  H  H  H  H  H  H  H  H  H
...
```

`pool.sbatch` passes `--times`, which appends the run to `times.csv` in the
shared folder for `speedup.py`. The time counts the rounds only, from when the
pool has started.

| Option | Meaning |
|---|---|
| `--workers` | Worker processes (default 4; `pool.sbatch` uses `--cpus-per-task`) |
| `--hands` | Hands per action (default 2,000,000; `pool.sbatch` takes `HANDS`) |
| `--table` | The starting table (default `table-round-1.csv`) |
| `--max-rounds` | Stop after this many rounds even if cells still flip (default 10) |
| `--out` | Write the final table to this CSV |
| `--times` | Append the run's time to this CSV |

## Compared with `mpi/mpi_policy.py`

The two programs split the cells the same way and do the same work, so any
difference in their times comes from how they run.

| | `mpi/mpi_policy.py` | `multiprocessing/pool_policy.py` |
|---|---|---|
| Started by | `mpiexec -n N`: N copies of the program | `python`: one program, which starts N workers |
| Who holds the table | Every rank, after each `bcast` | The main process |
| Sending out the table | `comm.bcast` | `pool.map`, with each worker's job |
| Collecting results | `comm.gather` | `pool.map`'s return value |
| Nodes | One or many | One |

## On a laptop

```
uv run python multiprocessing/pool_policy.py --workers 4 --times $BLACKJACK_LAB/times.csv
```

---

© 2026 Andrew Binkowski. All rights reserved.
