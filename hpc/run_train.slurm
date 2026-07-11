#!/bin/bash
#SBATCH --job-name=dynafeat_train
#SBATCH --output=logs/train_%j.out
#SBATCH --error=logs/train_%j.err
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=08:00:00
# ---- EDIT for your cluster ----
###SBATCH --partition=gpu
###SBATCH --account=your_alloc

# After preprocessing finishes (all shards), build the CDK2 split and train BOTH
# arms (baseline 80 vs +Dyna-1 81) with identical settings, then compare on CDK2.
set -euo pipefail
mkdir -p logs

# module load anaconda3 cuda
source activate "${ENV_NAME:-dynafeat}" 2>/dev/null || conda activate "${ENV_NAME:-dynafeat}"

ROOT="$HOME/dynamics-aware-featuredock"
OUT_DIR="${SCRATCH:-/scratch/mani.na}/dyna_featuredock_out"   # same dir preprocessing wrote to
OUT80="$OUT_DIR/pvar_80"; OUT81="$OUT_DIR/pvar_81"
RES="$OUT_DIR/results"; mkdir -p "$RES"
cd "$ROOT/featuredock"

# Optional: warm-start from FeatureDock's pretrained transformer checkpoints.
# Leave empty ("") to train from scratch. If set, matching layers are loaded and
# the shape-changed norm_layer (80->81) is reinitialized automatically.
# Repo ships: results/vit_20/HeavyAtomsite_transformer_20_seed{0,1,10,42,1234}.torch
WARM_START=""   # e.g. "$ROOT/featuredock/results/vit_20/HeavyAtomsite_transformer_20_seed42.torch"
WARM_ARG=""; [ -n "$WARM_START" ] && WARM_ARG="--warm-start $WARM_START"

# 1) Paper 3-way split (paper_cv): CDK2 = TEST (IsRemoved -1 fold), random 10%
#    of remaining clans = VAL, rest = TRAIN. Matches train_main.py lines 65-72.
# Skip the split if the PID lists already exist (deterministic; safe to reuse).
if [ -f "$OUT_DIR/test_pids.txt" ] && [ -f "$OUT_DIR/train_pids.txt" ] && [ -f "$OUT_DIR/val_pids.txt" ]; then
    echo "[skip] split lists already exist; reusing them"
else
    python -u src/curate_dataset/make_cdk2_split.py \
        --datafolder "$OUT81" --datadir "$ROOT/featuredock/data" \
        --cdk2-scope paper_cv --seed 42 --val-ratio 0.1 \
        --out-train "$OUT_DIR/train_pids.txt" --out-val "$OUT_DIR/val_pids.txt" \
        --out-test "$OUT_DIR/test_pids.txt"
fi
echo "--- split sizes ---"
echo "train: $(wc -l < "$OUT_DIR/train_pids.txt")  val: $(wc -l < "$OUT_DIR/val_pids.txt")  test(CDK2): $(wc -l < "$OUT_DIR/test_pids.txt")"

# 2) baseline (80 channels) -- skip if already trained
if [ -f "$RES/baseline80/baseline80_final_params.torch" ]; then
    echo "[skip] baseline80 already trained (final_params present)"
else
    python -u src/models/train_dynamics_aware.py \
        --modeltype transformer --feature_per_shell 80 --datafolder "$OUT80" \
        --train-pids "$OUT_DIR/train_pids.txt" --val-pids "$OUT_DIR/val_pids.txt" \
        --outfolder "$RES/baseline80" --modelname baseline80 \
        --steps 20 --n_structs 16 --lr 1e-3 --save_every 5 --num_workers 4 --use_gpu $WARM_ARG
fi

# 3) +Dyna-1 (81 channels), identical everything else -- skip if already trained
if [ -f "$RES/dyna1_81/dyna1_81_final_params.torch" ]; then
    echo "[skip] dyna1_81 already trained (final_params present)"
else
    python -u src/models/train_dynamics_aware.py \
        --modeltype transformer --feature_per_shell 81 --datafolder "$OUT81" \
        --train-pids "$OUT_DIR/train_pids.txt" --val-pids "$OUT_DIR/val_pids.txt" \
        --outfolder "$RES/dyna1_81" --modelname dyna1_81 \
        --steps 20 --n_structs 16 --lr 1e-3 --save_every 5 --num_workers 4 --use_gpu $WARM_ARG
fi

echo "[train] done. checkpoints + history under $RES/"
