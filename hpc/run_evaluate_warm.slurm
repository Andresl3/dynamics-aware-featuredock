#!/bin/bash
#SBATCH --job-name=dynafeat_eval_warm
#SBATCH --output=/home/mani.na/dyna_logs/eval_warm_%j.out
#SBATCH --error=/home/mani.na/dyna_logs/eval_warm_%j.err
#SBATCH --gres=gpu:v100-sxm2:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --partition=gpu

# CDK2 occupancy head-to-head for the WARM-START models: score the warm baseline
# (6x80) and warm +Dyna-1 (6x81) on the 18 held-out CDK2 test structures and
# write per-structure metrics, a summary, and a comparison figure. Fast (18
# structures, one forward pass each) -- runs fine on CPU too; drop --use_gpu and
# the --gres line if no GPU is free.
set -euo pipefail
mkdir -p /home/mani.na/dyna_logs

# module load anaconda3 cuda
source activate "${ENV_NAME:-dynafeat}" 2>/dev/null || conda activate "${ENV_NAME:-dynafeat}"

ROOT="/scratch/mani.na/dynamics-aware-featuredock"
OUT_DIR="$ROOT/dyna_featuredock_out"
RES="$OUT_DIR/results"
cd "$ROOT/featuredock"

BASELINE_CKPT="$RES/baseline80_warm/baseline80_warm_final_params.torch"
DYNA1_CKPT="$RES/dyna1_81_warm/dyna1_81_warm_final_params.torch"

for f in "$BASELINE_CKPT" "$DYNA1_CKPT"; do
    if [ ! -f "$f" ]; then echo "ERROR: checkpoint not found: $f"; exit 1; fi
done
echo "[eval-warm] baseline: $BASELINE_CKPT"
echo "[eval-warm] dyna1   : $DYNA1_CKPT"
echo "[eval-warm] test set: $OUT_DIR/test_pids.txt ($(wc -l < "$OUT_DIR/test_pids.txt") CDK2 structures)"

python -u src/models/evaluate_cdk2.py \
    --baseline-ckpt "$BASELINE_CKPT" --baseline-data "$OUT_DIR/pvar_80" \
    --dyna1-ckpt    "$DYNA1_CKPT"    --dyna1-data    "$OUT_DIR/pvar_81" \
    --test-pids     "$OUT_DIR/test_pids.txt" \
    --outdir        "$RES/cdk2_eval_warm" --use_gpu

echo "[eval-warm] done. results under $RES/cdk2_eval_warm/ :"
ls -la "$RES/cdk2_eval_warm/"
