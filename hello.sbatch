#!/bin/bash
# Hello, MPI, as a batch job:  sbatch --ntasks=8 hello.sbatch
#SBATCH --account=mpcs56430
#SBATCH --partition=caslake
#SBATCH --job-name=bj-hello
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --mem-per-cpu=1G
#SBATCH --time=00:05:00
#SBATCH --output=logs/%x-%j.out

uv run --offline mpiexec -n "$SLURM_NTASKS" python hello_mpi.py
