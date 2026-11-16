# MPI: every round in one job

One job runs every round. `mpiexec -n N` starts N copies of one program, the
**ranks**, numbered 0 to N − 1. They share no memory: rank 0 sends each round's
table to every rank, each rank simulates its share of the cells, and rank 0
collects the results and makes the next table. The ranks can be on one node or
many; this lab uses one.

Run every command from the repository's top folder (`~/blackjack`), where
`logs/` is.

| File | What it does |
|---|---|
| `hello_mpi.py` | The smallest MPI program: each rank prints its number, then rank 0 adds them up |
| `hello.sbatch` | Runs `hello_mpi.py` as a job |
| `mpi_policy.py` | Every round of policy iteration in one MPI program |
| `mpi.sbatch` | Runs `mpi_policy.py` as a job with any number of ranks |

MPI comes from the `mpich` package that `uv sync` installs, and Python reaches
it through `mpi4py`.

## Hello, MPI

```
uv run mpiexec -n 4 python mpi/hello_mpi.py     # login node: 4 ranks, a few seconds
sbatch --ntasks=8 mpi/hello.sbatch              # a compute node: 8 ranks
```

```
rank 3 of 4 on <node>
rank 0 of 4 on <node>
rank 0 received the sum of every rank: 6
rank 1 of 4 on <node>
rank 2 of 4 on <node>
```

Every rank runs the same program; each knows its own number (`rank`) and how
many ranks there are (`size`). The lines come out in a different order each
run, because the ranks run at the same time. Only rank 0 prints the sum,
because of `if rank == 0`. On a compute node with 8 ranks, the job's log in
`logs/bj-hello-<job id>.out` has 8 rank lines and the sum 28.

## One round

```
$ uv run mpiexec -n 4 python mpi/mpi_policy.py --max-rounds 1 --hands 100000
round 1:  41 cells flipped (   1.2 s)

4 ranks, 1 round, 100,000 hands per action: 1.2 s

       2  3  4  5  6  7  8  9 10  A
H4     H  H  H  H  H  H  H  H  H  H
H5     H  H  H  S  H  H  H  H  H  H
H6     H  H  S  S  S  H  H  H  H  H
...
```

`--max-rounds 1` stops after the first round: the same 41 flips as the job
array's round 1, from one program. With 100,000 hands per action it takes a
few seconds, short enough for a login node; at the default 2,000,000, one
round takes about a minute on 4 ranks, so run that as a job. Leave off
`--times` for a test like this, so it stays out of the class's `times.csv`.

## Every round in one job

```
sbatch --ntasks=8 mpi/mpi.sbatch                # 8 ranks on one node
squeue -u $USER
cat logs/bj-mpi-<job id>.out
```

`--ntasks` is the number of ranks. Each round:

1. `bcast`: rank 0 sends the current table to every rank
2. each rank simulates its share of the 270 cells: rank *r* takes cells *r*,
   *r* + N, *r* + 2N, ...
3. `gather`: rank 0 collects every rank's results
4. rank 0 switches each cell to the better action
5. `bcast`: rank 0 tells every rank whether anything changed

It stops when a round changes nothing. The log shows each round, the total
time and the final table:

```
round 1:  41 cells flipped (  34.5 s)
round 2:   5 cells flipped (  35.0 s)
round 3:   0 cells flipped (  33.4 s)

8 ranks, 3 rounds, 2,000,000 hands per action: 102.8 s

       2  3  4  5  6  7  8  9 10  A
H4     H  H  H  H  H  H  H  H  H  H
...
```

`mpi.sbatch` passes `--times`, which appends the run to `times.csv` in the
shared folder for `speedup.py`. The time counts the rounds only, from when
every rank has started.

| Option | Meaning |
|---|---|
| `--hands` | Hands per action (default 2,000,000; `mpi.sbatch` takes `HANDS`) |
| `--table` | The starting table (default `table-round-1.csv`) |
| `--max-rounds` | Stop after this many rounds even if cells still flip (default 10) |
| `--out` | Write the final table to this CSV |
| `--times` | Append the run's time to this CSV |

## On a laptop

```
uv run mpiexec -n 4 python mpi/hello_mpi.py
uv run mpiexec -n 4 python mpi/mpi_policy.py --times $BLACKJACK_LAB/times.csv
```

---

© 2026 Andrew Binkowski. All rights reserved.
