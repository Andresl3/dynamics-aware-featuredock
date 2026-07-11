#!/bin/bash
#SBATCH --job-name=rmsd_full18
#SBATCH --output=/home/mani.na/dyna_logs/rmsd18_%j.out
#SBATCH --error=/home/mani.na/dyna_logs/rmsd18_%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:v100-sxm2:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=08:00:00

# Full-18 CDK2 pose-RMSD head-to-head, BOTH regimes, paper settings.
#   --nsamples 500  (paper: 500 random rotations)  --topk 4  (paper selection)
#   --nthreads 16   (posing is CPU-bound; match --cpus-per-task)
# Reports per structure: top1 / top4 / ORACLE rmsd + oracle score & rank.
# The oracle-RMSD head-to-head is the clean model-quality comparison
# (baseline vs +Dyna-1) free of the scoring noise that dominates top-1/top-4.
# Runtime: ~3 min/structure/arm at 500 restarts x 16 cores -> 18 x 2 arms x 2
# regimes ~ 3-4 h. Fits the 8 h budget.
set -euo pipefail
mkdir -p /home/mani.na/dyna_logs

# --- batch-safe conda activation ---------------------------------------------
# In a non-interactive SLURM job the conda shell function does not exist yet,
# so `conda activate` fails with "Run 'conda init' before 'conda activate'".
# Fix: source conda's profile.d/conda.sh FIRST, then activate. Errors are NOT
# silenced, so any failure lands in the .err log instead of a mystery empty out.
#
# >>> SET THIS to the env you trained in (the ONLY value I can't infer) <<<
ENV_NAME="dynafeat"        # <-- CHANGE to your real cluster env name

# auto-locate conda.sh: from $CONDA_EXE if set, else the common base you use.
if [ -n "${CONDA_EXE:-}" ]; then
    source "$(dirname "$(dirname "$CONDA_EXE")")/etc/profile.d/conda.sh"
elif [ -f /shared/EL9/explorer/anaconda3/2024.06/etc/profile.d/conda.sh ]; then
    source /shared/EL9/explorer/anaconda3/2024.06/etc/profile.d/conda.sh
else
    echo "ERROR: cannot find conda.sh; set CONDA_EXE or edit this block"; exit 1
fi
conda activate "$ENV_NAME"
echo "[env] activated: $ENV_NAME -> $(which python)"
cd /scratch/mani.na/dynamics-aware-featuredock/featuredock

R=/scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out
NS=500; TK=4; NT=16

# ===== from-scratch (5-block) =====
python -u src/models/evaluate_cdk2_rmsd.py \
    --baseline-ckpt "$R/results/baseline80/baseline80_final_params.torch" \
    --baseline-data "$R/pvar_80" \
    --dyna1-ckpt    "$R/results/dyna1_81/dyna1_81_final_params.torch" \
    --dyna1-data    "$R/pvar_81" \
    --voxeldir "$R/voxels" --ligdir "$R/het" \
    --test-pids "$R/test_pids.txt" \
    --outdir "$R/results/cdk2_rmsd_scratch_full" \
    --nsamples $NS --topk $TK --prob-cutoff 0.5 --seed 0 --nthreads $NT --use_gpu

# ===== warm-start (20-block) =====
python -u src/models/evaluate_cdk2_rmsd.py \
    --baseline-ckpt "$R/results/baseline80_warm/baseline80_warm_final_params.torch" \
    --baseline-data "$R/pvar_80" \
    --dyna1-ckpt    "$R/results/dyna1_81_warm/dyna1_81_warm_final_params.torch" \
    --dyna1-data    "$R/pvar_81" \
    --voxeldir "$R/voxels" --ligdir "$R/het" \
    --test-pids "$R/test_pids.txt" \
    --outdir "$R/results/cdk2_rmsd_warm_full" \
    --nsamples $NS --topk $TK --prob-cutoff 0.5 --seed 0 --nthreads $NT --use_gpu

echo "=== from-scratch full-18 ==="; cat "$R/results/cdk2_rmsd_scratch_full/cdk2_rmsd_summary.csv"
echo "=== warm-start full-18 ===";  cat "$R/results/cdk2_rmsd_warm_full/cdk2_rmsd_summary.csv"
