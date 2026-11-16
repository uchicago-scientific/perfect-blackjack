#!/bin/bash
# Run rounds FIRST to LAST as a chain of Slurm jobs:
#
#   round 2 array -> assemble 2 -> round 3 array -> assemble 3 -> ...
#
# Each job waits for the one before it with --dependency=afterok, so the
# whole chain is submitted at once and Slurm starts each step when the last
# one succeeds. table-round-FIRST.csv must already exist.
#
#   bash chain.sh 2 4
set -euo pipefail
FIRST=${1:?first round}
LAST=${2:?last round}
mkdir -p logs

after=""
for ((r = FIRST; r <= LAST; r++)); do
    arr=$(sbatch --parsable $after --export=ALL,ROUND=$r array_round.sbatch)
    asm=$(sbatch --parsable --dependency=afterok:$arr --export=ALL,ROUND=$r assemble.sbatch)
    echo "round $r: array job $arr, then assemble job $asm"
    after="--dependency=afterok:$asm"
done
echo "watch it with:  squeue -u \$USER"
