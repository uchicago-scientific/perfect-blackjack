#!/bin/bash
# Every round of policy iteration in one MPI job, on one node. Submit from
# the repository's top folder, choosing the number of ranks with --ntasks:
#
#   sbatch --ntasks=8 mpi/mpi.sbatch
#
# One job, one allocation: the ranks pass the table and the results between
# them, so the rounds run back to back with no queue in between.
#SBATCH --account=mpcs56430
#SBATCH --partition=caslake
#SBATCH --job-name=bj-mpi
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=2G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.out

LAB=${BLACKJACK_LAB:-/project/mpcs56430/2026-autumn/blackjack}
export OMP_NUM_THREADS=1

uv run --offline mpiexec -n "$SLURM_NTASKS" python mpi/mpi_policy.py \
    --hands "${HANDS:-2000000}" --times "$LAB/times.csv"
