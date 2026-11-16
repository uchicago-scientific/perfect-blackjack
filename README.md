# Perfect Blackjack

Work out the best way to play every hand of blackjack by simulation, then run
the same calculation three ways and time them: as a **Slurm job array**, as
one **MPI** job, and as one Python program with a **multiprocessing** pool.
This is the in-class lab for Module 8 of MPCS 56430, Introduction to
Scientific Computing, at the University of Chicago. It runs on the Research
Computing Center's Midway3 cluster, and on a laptop.

The code is written: you run it and compare. The rules, Monte Carlo and
policy iteration are explained in [BACKGROUND.md](BACKGROUND.md).

## Setup on Midway3

On a login node (compute nodes have no internet access, so this has to run
here):

```
curl -LsSf https://astral.sh/uv/install.sh | sh    # install uv, once
source $HOME/.local/bin/env
git clone https://github.com/uchicago-scientific/perfect-blackjack.git ~/blackjack
cd ~/blackjack
uv sync --locked
mkdir -p logs
```

The first two lines install uv in `~/.local/bin` and put it on your `PATH`
for this session; later sessions find it on their own. If `uv --version`
already works, skip them. Run every command below from `~/blackjack`. Slurm
writes each job's output to `logs/`, and does not create that folder itself.

The example outputs in these READMEs come from a laptop, with the shared
folder shown as Midway3's. On Midway3 the cells, flips and tables are the
same; the times differ.

## Run it

### Score one cell

```
uv run python blackjack.py cell --hand H13 --up 2 --hands 100000
```

### 1. Slurm job array: [`slurm/`](slurm/)

Each round is 27 independent tasks, one per row, submitted as one array job.
Their results meet in files, and a separate job writes the next table. In
class, the instructor runs these and everyone watches the queue and the
shared folder.

```
sbatch --export=ALL,ROUND=1 slurm/array_round.sbatch   # round 1: all 27 rows
uv run python slurm/assemble.py --round 1              # the next table
bash slurm/chain.sh 2 4                                # rounds 2 to 4
```

### 2. MPI: [`mpi/`](mpi/)

One job runs every round. N copies of one program, the ranks, pass the table
and the results to each other as messages.

```
uv run mpiexec -n 4 python mpi/hello_mpi.py                                 # hello, login node
uv run mpiexec -n 4 python mpi/mpi_policy.py --max-rounds 1 --hands 100000  # one round, login node
sbatch --ntasks=8 mpi/mpi.sbatch                                            # every round, 8 ranks
```

### 3. multiprocessing: [`multiprocessing/`](multiprocessing/)

One job runs every round. One Python program starts N worker processes on one
node and hands them their cells with `pool.map`.

```
sbatch --cpus-per-task=8 multiprocessing/pool.sbatch    # every round, 8 workers
```

### Compare

Each MPI and multiprocessing job appends its time to `times.csv` in the shared
folder. In class, everyone counts off from 1 to 14 and runs both with the
same number of workers:

| Your number | Workers | Commands |
|---|---|---|
| 1 or 8 | 1 | `sbatch --ntasks=1 mpi/mpi.sbatch` and `sbatch --cpus-per-task=1 multiprocessing/pool.sbatch` |
| 2 or 9 | 2 | `sbatch --ntasks=2 mpi/mpi.sbatch` and `sbatch --cpus-per-task=2 multiprocessing/pool.sbatch` |
| 3 or 10 | 4 | `sbatch --ntasks=4 mpi/mpi.sbatch` and `sbatch --cpus-per-task=4 multiprocessing/pool.sbatch` |
| 4 or 11 | 8 | `sbatch --ntasks=8 mpi/mpi.sbatch` and `sbatch --cpus-per-task=8 multiprocessing/pool.sbatch` |
| 5 or 12 | 16 | `sbatch --ntasks=16 mpi/mpi.sbatch` and `sbatch --cpus-per-task=16 multiprocessing/pool.sbatch` |
| 6 or 13 | 32 | `sbatch --ntasks=32 mpi/mpi.sbatch` and `sbatch --cpus-per-task=32 multiprocessing/pool.sbatch` |
| 7 or 14 | 48 | `sbatch --ntasks=48 mpi/mpi.sbatch` and `sbatch --cpus-per-task=48 multiprocessing/pool.sbatch` |

Then the instructor computes the speedup of each:

```
uv run python speedup.py
```

```
$ uv run python speedup.py
method           workers  seconds  speedup efficiency
mpi                    1    254.7      1.0       100%
mpi                    2    144.4      1.8        88%
mpi                    4     97.8      2.6        65%
mpi                    8    102.8      2.5        31%
multiprocessing        1    249.7      1.0       100%
multiprocessing        2    137.6      1.8        91%
multiprocessing        4    106.6      2.3        59%
multiprocessing        8     98.5      2.5        32%
wrote /project/mpcs56430/2026-autumn/blackjack/speedup.png
```

It keeps the fastest run for each method and number of workers, and draws
`speedup.png`. **Speedup** S = T1 / TN is how many times faster than 1 worker;
**efficiency** E = S / N, where 100% is perfect. These numbers are from a
laptop with 4 fast cores and 4 slow ones, which is why 8 workers gain little
or nothing over 4; a Midway3 caslake node has 48 cores of one kind.

## Play

A web page deals blackjack by the lab's rules:
**<https://uchicago-scientific.github.io/perfect-blackjack/>**. To use it
offline, open `docs/index.html` from your copy of this repository in a
browser.

- **Coach:** after every choice, says whether the strategy chart agrees. The
  chart starts as basic strategy, the correct one
- **Deal:** buttons deal the four hands from the opening vote, or a hand you
  pick, every time until you choose another
- **Chart:** hidden until you press **Show chart**, so it doesn't give the
  answers away. Click a cell to switch it between H and S, or load the
  starting guess, a CSV file, or a table pasted from Midway3. **Download
  CSV** saves it
- **Simulate:** plays hit and stand from the current hand as many times as
  you choose, the same calculation as `blackjack.py cell`
- **Score:** plays whole hands by the chart, and by basic strategy on the
  same cards, so even a change to one cell shows

Keys: `h` hit, `s` stand, `n` next hand, `?` hint, `t` show or hide the
chart, `c` coach on or off.

To score charts from the command line, `blackjack.py score` plays a million
whole hands by each:

```
$ uv run python blackjack.py score table-round-1.csv basic-strategy.csv
1,000,000 hands each, a $1 bet on every hand
  table-round-1.csv        -0.0571 ± 0.0010 per hand: loses 5.7 cents per $1
  basic-strategy.csv       -0.0246 ± 0.0010 per hand: loses 2.5 cents per $1
```

Basic strategy's exact loss is 2.42 cents per $1, within the ± above. To score
your own chart, copy a table, change any H or S, and score it beside basic
strategy:

```
cp table-round-1.csv my-chart.csv
nano my-chart.csv
uv run python blackjack.py score my-chart.csv basic-strategy.csv
```

## The three ways

| | Slurm job array | MPI | multiprocessing |
|---|---|---|---|
| Jobs | 27 tasks and an assemble job, each round | One job, every round | One job, every round |
| Queue | Before every round | Once | Once |
| Results come together by | Files in the shared folder | Messages to rank 0 | `pool.map` returning them to the main process |
| Nodes | Any number | One or many | One |
| Started by | `sbatch --array` | `mpiexec -n N` | `Pool(N)` in the program |

[BACKGROUND.md](BACKGROUND.md#why-three-ways-to-run-it) says more.

## On a laptop

macOS, Linux or WSL. There is no Slurm, so run the commands inside the
`.sbatch` files directly:

```
git clone https://github.com/uchicago-scientific/perfect-blackjack.git
cd perfect-blackjack
uv sync --locked
export BLACKJACK_LAB=$PWD/shared
mkdir -p $BLACKJACK_LAB
cp table-round-1.csv $BLACKJACK_LAB/

for row in $(seq 0 26); do uv run python slurm/row.py --row $row --round 1; done
uv run python slurm/assemble.py --round 1
uv run mpiexec -n 4 python mpi/mpi_policy.py --times $BLACKJACK_LAB/times.csv
uv run python multiprocessing/pool_policy.py --workers 4 --times $BLACKJACK_LAB/times.csv
uv run python speedup.py
```

## Where results go

Every script reads and writes one shared folder:
`/project/mpcs56430/2026-autumn/blackjack` on Midway3, or whatever folder the
environment variable `BLACKJACK_LAB` names.

| Path | Written by | Holds |
|---|---|---|
| `table-round-1.csv` | The instructor, before class | The starting table |
| `round-N/row-NN.csv` | `slurm/row.py`, one per array task | Hit and stand for the 10 cells of row NN, in round N |
| `table-round-N.csv`, N ≥ 2 | `slurm/assemble.py --round N-1` | The table round N follows |
| `round-N.png` | `slurm/assemble.py --round N` | A heat map of round N |
| `times.csv` | `mpi/mpi_policy.py` and `multiprocessing/pool_policy.py`, with `--times` | One line per run: method, workers, seconds, rounds, hands, node |
| `speedup.png` | `speedup.py` | Time and speedup against workers, for each method |

## Files

```
blackjack.py          the game and the simulator, used by every script; scores a cell or a chart
table-round-1.csv     the starting table: hit on 16 or less, as the dealer does
basic-strategy.csv    the correct table for these rules, worked out exactly
speedup.py            speedup and efficiency of each method, from times.csv
slurm/                a round as a job array, and rounds as a job chain
mpi/                  every round in one MPI job, and hello, MPI
multiprocessing/      every round in one program with a pool of workers
docs/                 the web page: play with a coach, edit a chart, simulate and score it
BACKGROUND.md         the rules, Monte Carlo and policy iteration
pyproject.toml, uv.lock, .python-version    the environment, for uv sync --locked
```

`uv sync` installs `blackjack.py` as a module, so the scripts in each folder
can `import blackjack`. Each folder's README describes its scripts, with
example output.

## Common errors

| Symptom | Cause and fix |
|---|---|
| `uv: command not found` | uv isn't installed, or this session hasn't read the new `PATH`. Install it (see Setup), or run `source $HOME/.local/bin/env` |
| A job fails at once and `logs/` has nothing | It was submitted from a folder with no `logs/`. `cd ~/blackjack`, run `mkdir -p logs`, and submit again |
| `sbatch: error: Unable to open file` | The path to the `.sbatch` file is relative to where you are. Submit from `~/blackjack`, as `sbatch mpi/mpi.sbatch` |
| A job's log shows a uv error about working offline | `uv sync --locked` hasn't run on a login node yet. Run it there, then resubmit |
| `ModuleNotFoundError: No module named 'blackjack'` | The script ran outside the uv environment. Start it with `uv run` |
| `FileNotFoundError: .../table-round-2.csv` | Round 1 hasn't been assembled yet: run `slurm/assemble.py --round 1` |
| `PermissionError` writing to the shared folder | The folder or a `round-N` folder isn't writable by your group. Ask the instructor |
| `assemble.py` prints `missing rows ...` | Some array tasks failed or haven't finished. Check `squeue`, then run the `sbatch` line it prints |
| Chain steps stay pending with `(DependencyNeverSatisfied)` | An earlier step failed. `scancel` the rest, fix the cause, and start the chain again from the failed round |
| Results land in `/project/...` when you meant a local folder | `BLACKJACK_LAB` isn't set in this shell. `export` it again |

---

© 2026 Andrew Binkowski. All rights reserved.
