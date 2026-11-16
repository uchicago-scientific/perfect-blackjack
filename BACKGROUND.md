# Background: the problem

What the code in this repository calculates, and how. To run it, see the
[README](README.md).

- [The rules](#the-rules)
- [The strategy table](#the-strategy-table)
- [Monte Carlo: scoring one cell](#monte-carlo-scoring-one-cell)
- [Policy iteration: improving the whole table](#policy-iteration-improving-the-whole-table)
- [Why three ways to run it](#why-three-ways-to-run-it)
- [Reproducibility](#reproducibility)

## The rules

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

## The strategy table

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

## Monte Carlo: scoring one cell

To fill in one cell, play that hand many times each way, with random cards,
and score each result as a $1 bet: +1 for a win, 0 for a push, −1 for a
loss. The average score is the choice's **expected value**: what it wins or
loses per hand in the long run.

The standard error, printed as ±, says how much that average would change if
you ran it again. It shrinks with the square root of the number of hands:
100 times the hands gives one tenth the ±. Trust that one choice beats the
other only when the gap between them is bigger than twice its ±, where the
± of the gap is √(±hit² + ±stand²).

`blackjack.py cell` scores one cell and applies that test. At 1,000 hands per
action, hard 13 against a 2 is too close to call:

```
$ uv run python blackjack.py cell --hand H13 --up 2 --hands 1000
H13 vs 2, 1,000 hands each (after a hit, follow table-round-1.csv)
  stand -0.2540 ± 0.0306
  hit   -0.3350 ± 0.0288
  hit minus stand -0.0810, twice its ± 0.0841: too close to call
```

With 100 times the hands, the ± is a tenth as big and the answer is clear:

```
$ uv run python blackjack.py cell --hand H13 --up 2 --hands 100000
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

Keep `cell` runs on a Midway3 login node to a few seconds. To score a cell
against a later table, pass it, for example
`--table /project/mpcs56430/2026-autumn/blackjack/table-round-4.csv`.

## Policy iteration: improving the whole table

After a hit you have to choose again, and the simulation makes that choice by
looking it up in the table. So scoring the table needs a table. The lab starts
from a guess and improves it:

1. **Start:** `table-round-1.csv` copies the dealer's rule: H on 16 or less,
   S on 17 or more, against every upcard
2. **Score** hit and stand in all 270 cells, following the current table after
   a hit
3. **Switch** each cell to whichever choice scored better. A cell whose letter
   changes has **flipped**. The result is the next table
4. **Repeat** until a round flips nothing

At 2,000,000 hands per action, 41 cells flip in round 1, 5 in round 2 and
none in round 3. The final table matches the exact answer for these rules,
computed separately. A cell that is too close to call still takes whichever
action scored better.

## Why three ways to run it

Within a round, the 270 cells don't depend on each other, so they can run at
the same time on different CPUs. The next round needs all of them. The three
ways differ in how a round's results come together and how the next round
starts:

| | Slurm job array | MPI | multiprocessing |
|---|---|---|---|
| Who runs a round | 27 independent array tasks, one per row | N ranks of one program, each taking every Nth cell | N worker processes of one program, each taking every Nth cell |
| How results come together | Files in the shared folder, then a separate assemble job | `gather` to rank 0, which updates the table and `bcast`s it back | `pool.map` returns them to the main process, which updates the table |
| Between rounds | A new job, which waits in the queue | Nothing: the next round starts at once | Nothing: the next round starts at once |
| Nodes | Any number, any free CPUs | One or many | One |

MPI and multiprocessing split the cells the same way, so on one node they do
the same work; timing both shows what each costs to run. MPI's advantage is
that its ranks can be on different nodes, which share no memory.

## Reproducibility

Each cell's random numbers depend only on the cell (seed 56430), not on the
round or on which task, rank or worker runs it. The same table and number of
hands give the same results however the work is split: 27 array tasks, 1 MPI
rank or 48, 8 pool workers. It also means a round that flips nothing leaves
the table exactly as it was, so the rounds stop.

---

© 2026 Andrew Binkowski. All rights reserved.
