#!/bin/bash
#SBATCH --job-name=rmsd_screen
#SBATCH --output=/home/mani.na/dyna_logs/rmsd_screen_%A_%a.out
#SBATCH --error=/home/mani.na/dyna_logs/rmsd_screen_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:v100-sxm2:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --array=0-2          # one array task per target (p38a, hsp90a, ca2)

# RMSD screen (follow-up to occupancy) on a CAPPED 20-structure subset per target.
# Full-n 500-rot RMSD would be ~82 h across all three (CA-II alone 58 h) -> we cap
# at 20 random structures/target (~4 h each, matches CDK2's n=18). Both regimes.
#
# *** ILLUSTRATIVE, TRAIN-SET ***  All targets were in TRAINING (only CDK2 held
# out) -> memorisation, not generalisation; NOT comparable to CDK2 held-out.
# Paper-comparable pose metric is TOP-4 (paper CDK2 = 2.4 A); oracle is a
# best-case diagnostic, NOT a benchmark number. Label everything accordingly.
set -euo pipefail
mkdir -p /home/mani.na/dyna_logs

ENV_NAME="dynafeat"        # <-- CHANGE to your real cluster env name
if [ -n "${CONDA_EXE:-}" ]; then
    source "$(dirname "$(dirname "$CONDA_EXE")")/etc/profile.d/conda.sh"
elif [ -f /shared/EL9/explorer/anaconda3/2024.06/etc/profile.d/conda.sh ]; then
    source /shared/EL9/explorer/anaconda3/2024.06/etc/profile.d/conda.sh
else
    echo "ERROR: cannot find conda.sh; set CONDA_EXE or edit this block"; exit 1
fi
conda activate "$ENV_NAME"
cd /scratch/mani.na/dynamics-aware-featuredock/featuredock

R=/scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out
PIDDIR=/scratch/mani.na/dynamics-aware-featuredock/hpc/target_pids
NS=500; TK=4; NT=16

TARGETS=(p38a hsp90a ca2)
TGT=${TARGETS[$SLURM_ARRAY_TASK_ID]}
PIDS="$PIDDIR/${TGT}_rmsd20.txt"
echo "[env] $ENV_NAME -> $(which python)"
echo "############ RMSD: $TGT  (n=$(wc -l < "$PIDS"), 500 rot, top-4) ############"

# from-scratch
python -u src/models/evaluate_cdk2_rmsd.py \
    --baseline-ckpt "$R/results/baseline80/baseline80_final_params.torch" \
    --baseline-data "$R/pvar_80" \
    --dyna1-ckpt    "$R/results/dyna1_81/dyna1_81_final_params.torch" \
    --dyna1-data    "$R/pvar_81" \
    --voxeldir "$R/voxels" --ligdir "$R/het" \
    --test-pids "$PIDS" \
    --outdir "$R/results/rmsd_${TGT}_scratch" \
    --nsamples $NS --topk $TK --prob-cutoff 0.5 --seed 0 --nthreads $NT --use_gpu

# warm-start
python -u src/models/evaluate_cdk2_rmsd.py \
    --baseline-ckpt "$R/results/baseline80_warm/baseline80_warm_final_params.torch" \
    --baseline-data "$R/pvar_80" \
    --dyna1-ckpt    "$R/results/dyna1_81_warm/dyna1_81_warm_final_params.torch" \
    --dyna1-data    "$R/pvar_81" \
    --voxeldir "$R/voxels" --ligdir "$R/het" \
    --test-pids "$PIDS" \
    --outdir "$R/results/rmsd_${TGT}_warm" \
    --nsamples $NS --topk $TK --prob-cutoff 0.5 --seed 0 --nthreads $NT --use_gpu

echo "=== $TGT from-scratch ==="; cat "$R/results/rmsd_${TGT}_scratch/cdk2_rmsd_summary.csv"
echo "=== $TGT warm-start ===";  cat "$R/results/rmsd_${TGT}_warm/cdk2_rmsd_summary.csv"
