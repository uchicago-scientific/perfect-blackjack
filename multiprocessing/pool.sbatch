#!/bin/bash
# Every round of policy iteration in one Python program with a pool of
# workers, on one node. Submit from the repository's top folder, choosing
# the number of workers with --cpus-per-task:
#
#   sbatch --cpus-per-task=8 multiprocessing/pool.sbatch
#
# One job, one process, one CPU per worker: the workers get the table and
# return their results through the main process, so the rounds run back to
# back with no queue in between.
#SBATCH --account=mpcs56430
#SBATCH --partition=caslake
#SBATCH --job-name=bj-pool
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=2G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.out

LAB=${BLACKJACK_LAB:-/project/mpcs56430/2026-autumn/blackjack}
export OMP_NUM_THREADS=1

uv run --offline python multiprocessing/pool_policy.py --workers "$SLURM_CPUS_PER_TASK" \
    --hands "${HANDS:-2000000}" --times "$LAB/times.csv"
