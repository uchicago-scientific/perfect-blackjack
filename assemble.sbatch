#!/bin/bash
# Collect a round's rows and write the next table. chain.sh runs this after
# each round's array job.
#SBATCH --account=mpcs56430
#SBATCH --partition=caslake
#SBATCH --job-name=bj-assemble
#SBATCH --ntasks=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=logs/%x-%j.out

uv run --offline python assemble.py --round "${ROUND:?set ROUND}"
