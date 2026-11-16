# Perfect Blackjack

Work out how to play every hand of blackjack by simulation, and run the same
calculation two ways on a cluster: as a Slurm **job array**, and as one
**MPI** job. This is the in-class lab for Module 8 of MPCS 56430,
Introduction to Scientific Computing, at the University of Chicago. It runs
on the Research Computing Center's Midway3 cluster, and on a laptop.

The code is written. You run it, look at what it prints, and compare the two
ways of running it.

## Contents

- [The problem](#the-problem)
- [Setup](#setup)
- [The shared folder](#the-shared-folder)
- [Files](#files)
- [The scripts, with examples](#the-scripts-with-examples)
- [The lab on Midway3, step by step](#the-lab-on-midway3-step-by-step)
- [Common errors](#common-errors)

## The problem

### The rules

A simplified blackjack:

- Cards 2 to 9 count their number, 10, J, Q and K count 10, and an ace counts
  11 or 1. Every card is drawn with replacement (an infinite deck), so the
  chances never change
- You and the dealer each get two cards. You see one of the dealer's cards,
  the **upcard**
- You play first. You **hit** (take a card) or **stand** (stop), as often as
  you like. Go over 21 and you **bust**: you lose at once
- Then the dealer plays by a fixed rule: hit on 16 or less, stand on 17 or
  more, including soft 17 (an ace and a 6)
- Closer to 21 wins. A tie is a push: your bet comes back
- Blackjack (21 in your first two cards) pays 3 to 2. A dealer blackjack
  beats every other hand
- Only hit or stand: no doubling, splitting, surrender or insurance

A hand is **soft** when it holds an ace counted as 11, so one more card can't
bust it. Every other hand is **hard**.

### The strategy table

The answer is a table that says H or S for every hand you might hold against
every dealer upcard:

- 27 rows, one per hand: hard 4 to 21 (rows 0 to 17), then soft 13 to 21
  (rows 18 to 26). Two aces, soft 12, is always a hit and has no row
- 10 columns, one per dealer upcard: 2 to 10, and ace
- 270 cells, numbered row by row: cell 0 is hard 4 against a 2, cell 10 is
  hard 5 against a 2, cell 269 is soft 21 against an ace

Tables are stored as CSV files, one row per hand. This is the start of
`table-round-1.csv`:

```
hand,2,3,4,5,6,7,8,9,10,A
H4,H,H,H,H,H,H,H,H,H,H
H5,H,H,H,H,H,H,H,H,H,H
```

### Monte Carlo

To fill in one cell, play that hand many times each way, with random cards,
and score each result as a $1 bet: +1 for a win, 0 for a push, −1 for a
loss. The average score is the choice's **expected value**: what it wins or
loses per hand in the long run. The standard error, printed as ±, says how
much that average would change if you ran it again. It shrinks with the
square root of the number of hands. Trust that one choice beats the other
only when the gap between them is bigger than about twice its ±.

### Policy iteration

After a hit you have to choose again, and the simulation makes that choice
by looking it up in the table. So scoring the table needs a table. The lab
starts from a guess and improves it:

1. **Start:** `table-round-1.csv` copies the dealer's rule: H on 16 or less,
   S on 17 or more, against every upcard
2. **Score** hit and stand in all 270 cells, following the current table after
   a hit
3. **Switch** each cell to whichever choice scored better. A cell whose letter
   changes has **flipped**. The result is the next table
4. **Repeat** until a round flips nothing

At 400,000 hands per action, 41 cells flip in round 1, 5 in round 2 and none
in round 3. The final table matches the exact answer for these rules,
computed separately.

Within a round the 270 cells don't depend on each other, so they can run at
the same time on different CPUs. The next round has to wait for all of them.
That is what the two ways of running it handle differently:

| | Job array and job chain | One MPI job |
|---|---|---|
| Who runs a round | 27 independent array tasks, one per row | N ranks of one program, each taking every Nth cell |
| How results come together | Files in the shared folder, then a separate assemble job | `gather` to rank 0, which updates the table and `bcast`s it back |
| Between rounds | A new job, which waits in the queue | Nothing: the next round starts at once |

### Reproducibility

Each cell's random numbers depend only on the cell (seed 56430), not on the
round or on which task or rank runs it. The same table and number of hands
give the same results however the work is split: 27 array tasks, 1 MPI rank
or 48. It also means a round that flips nothing leaves the table exactly as
it was, so the rounds stop.

## Setup

### On Midway3

On a login node (compute nodes have no internet access, so this has to run
here):

```
git clone https://github.com/uchicago-scientific/perfect-blackjack.git ~/blackjack
cd ~/blackjack
uv sync --locked
mkdir -p logs
```

`uv sync --locked` installs Python 3.13 and the packages in `uv.lock`: NumPy,
Matplotlib, `mpi4py` and the `mpich` MPI library. The batch scripts run with
`uv run --offline`, which uses that environment and never downloads. Slurm
writes each job's output to `logs/`, and does not create that folder itself.

If `uv` is not installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`,
then sign out and back in.

### On a laptop

macOS, Linux or WSL. There is no Slurm, so run the commands inside the
`.sbatch` files directly:

```
git clone https://github.com/uchicago-scientific/perfect-blackjack.git
cd perfect-blackjack
uv sync --locked
export BLACKJACK_LAB=$PWD/shared
mkdir -p $BLACKJACK_LAB
cp table-round-1.csv $BLACKJACK_LAB/
```

## The shared folder

Every script reads and writes one shared folder:
`/project/mpcs56430/2026-autumn/blackjack` on Midway3, or whatever folder the
environment variable `BLACKJACK_LAB` names.

| Path | Written by | Holds |
|---|---|---|
| `table-round-1.csv` | The instructor, before class | The starting table |
| `round-N/row-NN.csv` | `blackjack.py row`, one per array task | Hit and stand for the 10 cells of row NN, in round N |
| `table-round-N.csv`, N ≥ 2 | `assemble.py --round N-1` | The table round N follows |
| `round-N.png` | `assemble.py --round N` | A heat map of round N |
| `mpi-times.csv` | `mpi_policy.py --times` | One line per MPI run: ranks, seconds, rounds |
| `speedup.png` | `speedup.py` | The class's speedup plot |

## Files

| File | What it is |
|---|---|
| `blackjack.py` | The game, the simulator and the table files. `cell` prints one cell; `row` writes one row of results for a round |
| `table-round-1.csv` | The starting table |
| `array_round.sbatch` | One round as a job array: one task per row |
| `assemble.py` | Collects a round's rows, writes the next table and a heat map |
| `assemble.sbatch` | Runs `assemble.py` as a job, for the chain |
| `chain.sh` | Submits several rounds at once, each step waiting for the last with `--dependency=afterok` |
| `hello_mpi.py`, `hello.sbatch` | The smallest MPI program, on the login node or as a job |
| `mpi_policy.py` | Every round of policy iteration in one MPI program |
| `mpi.sbatch` | Runs `mpi_policy.py` as a job with any number of ranks |
| `speedup.py` | Speedup and efficiency from everyone's MPI times |
| `pyproject.toml`, `uv.lock`, `.python-version` | The environment, for `uv sync --locked` |

## The scripts, with examples

The outputs below are from a laptop run. On Midway3 the cells, flips and
values are the same; times differ. `<id>` and `<node>` stand for a job id
and a host name.

### `blackjack.py cell`: one cell, printed

```
uv run python blackjack.py cell --hand H13 --up 2 --hands 1000
```

```
H13 vs 2, 1,000 hands each (after a hit, follow table-round-1.csv)
  stand -0.2540 ± 0.0306
  hit   -0.3350 ± 0.0288
  hit minus stand -0.0810, twice its ± 0.0841: too close to call
```

With 100 times the hands, the ± is a tenth as big and the answer is clear:

```
uv run python blackjack.py cell --hand H13 --up 2 --hands 100000
```

```
H13 vs 2, 100,000 hands each (after a hit, follow table-round-1.csv)
  stand -0.2926 ± 0.0030
  hit   -0.3365 ± 0.0029
  hit minus stand -0.0439, twice its ± 0.0083: stand is better
```

| Option | Meaning |
|---|---|
| `--hand` | `H` or `S` and a total: `H13` is hard 13, `S17` is soft 17 |
| `--up` | The dealer's upcard: `2` to `10`, or `A` |
| `--hands` | Hands played for each action (default 100,000) |
| `--table` | The table followed after a hit (default `table-round-1.csv`) |

Keep `cell` runs on a login node short: a few seconds. To score a cell
against a later table, pass it, for example
`--table /project/mpcs56430/2026-autumn/blackjack/table-round-3.csv`.

### `blackjack.py row`: one row of a round, written to a file

What each array task runs:

```
uv run python blackjack.py row --row 12 --round 1
```

```
round 1: wrote /project/mpcs56430/2026-autumn/blackjack/round-1/row-12.csv
```

It reads `table-round-1.csv`, simulates the 10 cells of row 12 (hard 16) at
400,000 hands per action, and writes:

```
cell,hand,up,hands,stand,stand_se,hit,hit_se
120,H16,2,400000,-0.290275,0.001513,-0.470492,0.001349
121,H16,3,400000,-0.25385,0.001529,-0.463838,0.001357
```

`--hands`, `--table` and `--out` override the defaults.

### `array_round.sbatch`: a round as a job array

One array task per row, each running `blackjack.py row` with its task number
as the row. The tasks are independent: none waits for or talks to another.

```
sbatch --export=ALL,ROUND=1 array_round.sbatch               # all 27 rows
sbatch --array=4-5 --export=ALL,ROUND=1 array_round.sbatch   # rows 4 and 5
squeue -u $USER                                              # PD waiting, R running
cat logs/bj-array-<job id>_4.out                             # task 4's output
```

`--export=ALL,ROUND=1` passes `ROUND=1` to the script, along with your
environment. `HANDS` can be passed the same way; the default is 400,000.

### `assemble.py`: put a round together

```
uv run python assemble.py --round 1
```

```
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
call). It can run while rows are still arriving. If rows are missing it
writes the heat map with dots for the missing cells, prints the `sbatch` line
that reruns them, and exits with status 1 without writing the next table:

```
Round 1: 10 of 270 cells, 5 flipped, 1 too close to call
wrote /project/mpcs56430/2026-autumn/blackjack/round-1.png
missing rows 0-11,13-26: rerun with  sbatch --array=0-11,13-26 --export=ALL,ROUND=1 array_round.sbatch
```

A cell that is too close to call still takes whichever action scored better.

### `chain.sh`: several rounds as a job chain

```
bash chain.sh 2 4
```

```
round 2: array job <id>, then assemble job <id>
round 3: array job <id>, then assemble job <id>
round 4: array job <id>, then assemble job <id>
watch it with:  squeue -u $USER
```

It submits every step at once. Each step starts only when the one before it
succeeds (`--dependency=afterok`), so `squeue` shows the waiting steps with
the reason `(Dependency)`. If a step fails, the steps after it can never
start and show `(DependencyNeverSatisfied)`; cancel them with `scancel`.
`table-round-2.csv` must exist before `bash chain.sh 2 ...`.

### `hello_mpi.py`: the smallest MPI program

Every rank runs the same program; each knows its own number (its rank) and
how many ranks there are.

```
uv run mpiexec -n 4 python hello_mpi.py      # login node: 4 ranks, a few seconds
sbatch --ntasks=8 hello.sbatch               # a compute node: 8 ranks
```

```
rank 0 of 4 on <node>
rank 0 received the sum of every rank: 6
rank 1 of 4 on <node>
rank 2 of 4 on <node>
rank 3 of 4 on <node>
```

The lines come out in a different order each run, because the ranks run at
the same time. Only rank 0 prints the sum.

### `mpi_policy.py` and `mpi.sbatch`: every round in one MPI job

Each round, rank 0 broadcasts the table, every rank simulates its share of
the cells (rank r takes cells r, r + N, r + 2N, ...), rank 0 gathers the
results and updates the table, then tells every rank whether to stop.

```
sbatch --ntasks=16 mpi.sbatch                # 16 ranks on one node
cat logs/bj-mpi-<job id>.out
```

On a laptop: `uv run mpiexec -n 4 python mpi_policy.py`.

```
round 1:  41 cells flipped (   5.4 s)
round 2:   5 cells flipped (   5.2 s)
round 3:   0 cells flipped (   5.2 s)

4 ranks, 3 rounds, 400,000 hands per action: 15.8 s

       2  3  4  5  6  7  8  9 10  A
H4     H  H  H  H  H  H  H  H  H  H
...
```

`mpi.sbatch` adds `--times`, which appends the run to `mpi-times.csv`. The
time counts the rounds only, from when every rank has started.

| Option | Meaning |
|---|---|
| `--hands` | Hands per action (default 400,000; `mpi.sbatch` takes `HANDS`) |
| `--table` | The starting table (default `table-round-1.csv`) |
| `--max-rounds` | Stop after this many rounds even if cells still flip (default 10) |
| `--out` | Write the final table to this CSV |
| `--times` | Append the run's time to this CSV |

### `speedup.py`: the class's speedup

```
uv run python speedup.py
```

```
ranks  seconds  speedup efficiency
    1     49.1      1.0       100%
    4     15.8      3.1        78%
wrote /project/mpcs56430/2026-autumn/blackjack/speedup.png
```

It keeps the fastest run at each rank count. Speedup is S = T1 / TN, how many
times faster than 1 rank; efficiency is E = S / N, where 100% is perfect.

## The lab on Midway3, step by step

1. **Set up** on a login node (see [Setup](#setup)), and try a cell with
   `blackjack.py cell`
2. **Round 1, as a job array.** The class splits the 27 rows: number k of 14
   runs rows 2k − 2 and 2k − 1, and number 14 runs row 26. Number 3, for
   example: `sbatch --array=4-5 --export=ALL,ROUND=1 array_round.sbatch`
3. **Assemble round 1** (instructor): `uv run python assemble.py --round 1`
4. **Rounds 2 to 4, as a chain** (instructor): `bash chain.sh 2 4`. Everyone
   can watch with `squeue -u <instructor's CNetID>`
5. **Hello, MPI:** `uv run mpiexec -n 4 python hello_mpi.py`, then
   `sbatch --ntasks=8 hello.sbatch`
6. **Every round in one MPI job,** each person with a different number of
   ranks: numbers 1 and 8 run 1 rank, 2 and 9 run 2, 3 and 10 run 4, 4 and 11
   run 8, 5 and 12 run 16, 6 and 13 run 32, 7 and 14 run 48:
   `sbatch --ntasks=<ranks> mpi.sbatch`
7. **Speedup** (instructor): `uv run python speedup.py`

## Common errors

| Symptom | Cause and fix |
|---|---|
| `uv: command not found` | uv isn't installed, or this session hasn't read the new `PATH`. Install it (see Setup), or run `source $HOME/.local/bin/env` |
| A job fails at once and `logs/` has nothing | The `logs` folder doesn't exist, and Slurm doesn't create it. Run `mkdir -p logs` in `~/blackjack` |
| A job's log shows a uv error about working offline | `uv sync --locked` hasn't run on a login node yet. Run it there, then resubmit |
| `FileNotFoundError: .../table-round-2.csv` | Round 1 hasn't been assembled yet: run `assemble.py --round 1` |
| `PermissionError` writing to the shared folder | The folder or a `round-N` folder isn't writable by your group. Ask the instructor |
| `assemble.py` prints `missing rows ...` | Some array tasks failed or haven't finished. Check `squeue`, then run the `sbatch` line it prints |
| Chain steps stay pending with `(DependencyNeverSatisfied)` | An earlier step failed. `scancel` the rest, fix the cause, and start the chain again from the failed round |
| Results land in `/project/...` when you meant a local folder | `BLACKJACK_LAB` isn't set in this shell. `export` it again |

---

© 2026 Andrew Binkowski. All rights reserved.
