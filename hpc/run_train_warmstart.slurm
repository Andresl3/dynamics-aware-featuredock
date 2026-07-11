#!/bin/bash
#SBATCH --job-name=dynafeat_warm
#SBATCH --output=/home/mani.na/dyna_logs/warm_%j.out
#SBATCH --error=/home/mani.na/dyna_logs/warm_%j.err
#SBATCH --gres=gpu:v100-sxm2:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --partition=gpu

# WARM-START variant: fine-tune both arms (baseline 6x80 vs +Dyna-1 6x81) from
# FeatureDock's pretrained transformer checkpoint instead of from random init.
#
# IMPORTANT: the pretrained checkpoint is the 20-BLOCK "vit_20" model
# (n_blocks=20, hidden=64, heads=2, ~512K params) -- NOT the 5-block model the
# from-scratch runs used. Both arms MUST be built with --n_blocks 20 so the
# architecture matches the checkpoint, otherwise the load is invalid.
# Verified locally: fps=80 loads 334/334 tensors (0 mismatch); fps=81 loads
# 330/334 and reinitializes exactly the 4 norm_layer tensors (BatchNorm2d 80->81).
#
# Results go to results/baseline80_warm and results/dyna1_81_warm so they do NOT
# overwrite the from-scratch results/baseline80 and results/dyna1_81.
set -euo pipefail
mkdir -p /home/mani.na/dyna_logs

# The 20-block model is ~4x bigger than the 5-block from-scratch model, so batch
# size is lowered (n_structs 16 -> 4) to fit the V100's 32 GB. This env var lets
# the allocator grow segments to reduce fragmentation OOMs.
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# module load anaconda3 cuda
source activate "${ENV_NAME:-dynafeat}" 2>/dev/null || conda activate "${ENV_NAME:-dynafeat}"

ROOT="/scratch/mani.na/dynamics-aware-featuredock"
OUT_DIR="$ROOT/dyna_featuredock_out"
OUT80="$OUT_DIR/pvar_80"; OUT81="$OUT_DIR/pvar_81"
RES="$OUT_DIR/results"; mkdir -p "$RES"
cd "$ROOT/featuredock"

# Pretrained 20-block checkpoint (seed 42). Nested path + _best_checkpoint_params.
CKPT="$ROOT/featuredock/results/vit_20/HeavyAtomsite_transformer_20_seed42/HeavyAtomsite_transformer_20_seed42_best_checkpoint_params.torch"
if [ ! -f "$CKPT" ]; then
    echo "ERROR: pretrained checkpoint not found at:"; echo "  $CKPT"
    echo "Available vit_20 checkpoints:"; ls "$ROOT/featuredock/results/vit_20/"*/*_best_checkpoint_params.torch 2>/dev/null
    exit 1
fi
echo "[warm] pretrained checkpoint: $CKPT"

# 1) Split (paper_cv): CDK2 = TEST, random 10% of remaining clans = VAL. Fast/deterministic.
python src/curate_dataset/make_cdk2_split.py \
    --datafolder "$OUT81" --datadir "$ROOT/featuredock/data" \
    --cdk2-scope paper_cv --seed 42 --val-ratio 0.1 \
    --out-train "$OUT_DIR/train_pids.txt" --out-val "$OUT_DIR/val_pids.txt" \
    --out-test "$OUT_DIR/test_pids.txt"
echo "--- split sizes ---"
echo "train: $(wc -l < "$OUT_DIR/train_pids.txt")  val: $(wc -l < "$OUT_DIR/val_pids.txt")  test(CDK2): $(wc -l < "$OUT_DIR/test_pids.txt")"

# 2) baseline (80 channels), warm-started, 20-block architecture
if [ -f "$RES/baseline80_warm/baseline80_warm_final_params.torch" ]; then
    echo "[skip] baseline80_warm already trained"
else
    python -u src/models/train_dynamics_aware.py \
        --modeltype transformer --feature_per_shell 80 --n_blocks 20 --datafolder "$OUT80" \
        --train-pids "$OUT_DIR/train_pids.txt" --val-pids "$OUT_DIR/val_pids.txt" \
        --outfolder "$RES/baseline80_warm" --modelname baseline80_warm \
        --warm-start "$CKPT" \
        --steps 20 --n_structs 4 --lr 1e-3 --save_every 5 --num_workers 4 --use_gpu
fi

# 3) +Dyna-1 (81 channels), warm-started, identical everything else
if [ -f "$RES/dyna1_81_warm/dyna1_81_warm_final_params.torch" ]; then
    echo "[skip] dyna1_81_warm already trained"
else
    python -u src/models/train_dynamics_aware.py \
        --modeltype transformer --feature_per_shell 81 --n_blocks 20 --datafolder "$OUT81" \
        --train-pids "$OUT_DIR/train_pids.txt" --val-pids "$OUT_DIR/val_pids.txt" \
        --outfolder "$RES/dyna1_81_warm" --modelname dyna1_81_warm \
        --warm-start "$CKPT" \
        --steps 20 --n_structs 4 --lr 1e-3 --save_every 5 --num_workers 4 --use_gpu
fi

echo "[warm] done. checkpoints + history under $RES/{baseline80_warm,dyna1_81_warm}/"
