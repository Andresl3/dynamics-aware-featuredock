#!/bin/bash
#SBATCH --job-name=dynafeat_eval
#SBATCH --output=/home/mani.na/dyna_logs/eval_%j.out
#SBATCH --error=/home/mani.na/dyna_logs/eval_%j.err
#SBATCH --gres=gpu:v100-sxm2:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --partition=gpu

# CDK2 head-to-head: score the trained baseline (6x80) and +Dyna-1 (6x81) models
# on the 18 held-out CDK2 test structures and write per-structure metrics, a
# summary, and a comparison figure. Fast (18 structures, one forward pass each) --
# runs fine on CPU too; drop --use_gpu and the --gres line if no GPU is free.
set -euo pipefail
mkdir -p /home/mani.na/dyna_logs

# module load anaconda3 cuda
source activate "${ENV_NAME:-dynafeat}" 2>/dev/null || conda activate "${ENV_NAME:-dynafeat}"

ROOT="/scratch/mani.na/dynamics-aware-featuredock"
OUT_DIR="$ROOT/dyna_featuredock_out"
RES="$OUT_DIR/results"
cd "$ROOT/featuredock"

BASELINE_CKPT="$RES/baseline80/baseline80_final_params.torch"
DYNA1_CKPT="$RES/dyna1_81/dyna1_81_final_params.torch"

# If the dyna1 final save was rescued to home (ESTALE fallback), use that copy.
if [ ! -f "$DYNA1_CKPT" ] && [ -f "$HOME/dynafeat_rescue_dyna1_81/dyna1_81_final_params.torch" ]; then
    DYNA1_CKPT="$HOME/dynafeat_rescue_dyna1_81/dyna1_81_final_params.torch"
    echo "[eval] using rescued dyna1 checkpoint: $DYNA1_CKPT"
fi
if [ ! -f "$HOME/dynafeat_rescue_baseline80/baseline80_final_params.torch" ] && [ ! -f "$BASELINE_CKPT" ]; then
    echo "ERROR: baseline checkpoint not found at $BASELINE_CKPT"; exit 1
fi
[ ! -f "$BASELINE_CKPT" ] && BASELINE_CKPT="$HOME/dynafeat_rescue_baseline80/baseline80_final_params.torch"

echo "[eval] baseline: $BASELINE_CKPT"
echo "[eval] dyna1   : $DYNA1_CKPT"
echo "[eval] test set: $OUT_DIR/test_pids.txt ($(wc -l < "$OUT_DIR/test_pids.txt") CDK2 structures)"

python -u src/models/evaluate_cdk2.py \
    --baseline-ckpt "$BASELINE_CKPT" --baseline-data "$OUT_DIR/pvar_80" \
    --dyna1-ckpt    "$DYNA1_CKPT"    --dyna1-data    "$OUT_DIR/pvar_81" \
    --test-pids     "$OUT_DIR/test_pids.txt" \
    --outdir        "$RES/cdk2_eval" --use_gpu

echo "[eval] done. results under $RES/cdk2_eval/ :"
ls -la "$RES/cdk2_eval/"
