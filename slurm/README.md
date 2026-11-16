# Slurm: a job array and a job chain

One round of the table as a **job array**: 27 independent tasks, one per row
of 10 cells. Each task writes its results to a file in the shared folder; a
separate job reads the files and writes the next round's table. Later rounds
run as a **job chain**: each round's array, then its assemble job, each
waiting for the step before it.

Run every command from the repository's top folder (`~/blackjack`), where
`logs/` is.

| File | What it does |
|---|---|
| `row.py` | One row of one round: what each array task runs |
| `array_round.sbatch` | One round as a job array, one task per row |
| `assemble.py` | Collects a round's rows, writes the next table and a heat map |
| `assemble.sbatch` | Runs `assemble.py` as a job, for the chain |
| `chain.sh` | Submits several rounds at once, each step waiting for the last |

## Round 1 as a job array

```
sbatch --export=ALL,ROUND=1 slurm/array_round.sbatch               # all 27 rows
sbatch --array=4-5 --export=ALL,ROUND=1 slurm/array_round.sbatch   # rows 4 and 5
squeue -u $USER                                                    # PD waiting, R running
cat logs/bj-array-<job id>_4.out                                   # task 4's output
```

`--array` on the command line overrides the file's `--array=0-26`. Task *k*
gets `$SLURM_ARRAY_TASK_ID` = *k* and simulates row *k*. `--export=ALL,ROUND=1`
passes `ROUND=1` to the script, along with your environment; `HANDS` can be
passed the same way (default 2,000,000).

In class, the 27 rows are split: number *k* of 14 runs rows 2*k* − 2 and
2*k* − 1, and number 14 runs row 26. Number 3 runs `--array=4-5`.

Each task runs `row.py`:

```
$ uv run python slurm/row.py --row 12 --round 1
round 1: wrote /project/mpcs56430/2026-autumn/blackjack/round-1/row-12.csv
```

It reads `table-round-1.csv`, simulates the 10 cells of row 12 (hard 16) at
2,000,000 hands per action, and writes:

```
cell,hand,up,hands,stand,stand_se,hit,hit_se
120,H16,2,2000000,-0.292063,0.000676,-0.470776,0.000604
121,H16,3,2000000,-0.251965,0.000684,-0.463018,0.000607
```

`--hands`, `--table` and `--out` override the defaults.

## Put a round together

```
$ uv run python slurm/assemble.py --round 1
Round 1: 270 of 270 cells, 41 flipped, 1 too close to call
wrote /project/mpcs56430/2026-autumn/blackjack/round-1.png
wrote /project/mpcs56430/2026-autumn/blackjack/table-round-2.csv
  flipped H5 vs 5: now stand
  flipped H6 vs 4: now stand
  ...
```

It reads every `row-NN.csv` for the round, switches each cell to the better
action, and writes the next table and a heat map of the round (orange: hit is
better, purple: stand is better; gold outline: flipped; hatched: too close to
call). It can run while rows are still arriving. If rows are missing, it
writes the heat map with dots for the missing cells, prints the `sbatch` line
that reruns them, and exits with status 1 without writing the next table:

```
Round 1: 100 of 270 cells, 15 flipped, 1 too close to call
wrote /project/mpcs56430/2026-autumn/blackjack/round-1.png
missing rows 0-9,20-26: rerun with  sbatch --array=0-9,20-26 --export=ALL,ROUND=1 slurm/array_round.sbatch
```

`--compare <table.csv>` outlines in red the cells that differ from another
table.

## Rounds 2 and on as a job chain

```
$ bash slurm/chain.sh 2 4
round 2: array job <id>, then assemble job <id>
round 3: array job <id>, then assemble job <id>
round 4: array job <id>, then assemble job <id>
watch it with:  squeue -u $USER
```

It submits every step at once. Each step starts only when the one before it
succeeds (`--dependency=afterok`), so `squeue` shows the waiting steps with
the reason `(Dependency)`. If a step fails, the steps after it can never
start and show `(DependencyNeverSatisfied)`; cancel them with `scancel`.
`table-round-2.csv` must exist before `bash slurm/chain.sh 2 ...`.

To time the whole chain, from the first submit to the last end:

```
sacct -X -S today --name=bj-array,bj-assemble --format=JobName,Submit,Start,End
```

The chain's time is the last `End` minus the first `Submit`. Between a step's
`Submit` and its `Start` it was waiting: for the step before it, then for
free CPUs.

## On a laptop

There is no Slurm, so run the tasks one after another, then assemble:

```
for row in $(seq 0 26); do uv run python slurm/row.py --row $row --round 1; done
uv run python slurm/assemble.py --round 1
```

---

© 2026 Andrew Binkowski. All rights reserved.
