#!/bin/bash
# One round of the blackjack table as a job array: one task per row of 10
# cells. Choose the rows and the round on the command line:
#
#   sbatch --array=4-5 --export=ALL,ROUND=1 array_round.sbatch
#
# Every task is independent: it reads the round's table, simulates its row,
# and writes row-NN.csv to the round's folder. No task talks to another.
#SBATCH --account=mpcs56430
#SBATCH --partition=caslake
#SBATCH --job-name=bj-array
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --array=0-26
#SBATCH --output=logs/%x-%A_%a.out

ROUND=${ROUND:-1}
HANDS=${HANDS:-400000}

uv run --offline python blackjack.py row \
    --row "$SLURM_ARRAY_TASK_ID" --round "$ROUND" --hands "$HANDS"
