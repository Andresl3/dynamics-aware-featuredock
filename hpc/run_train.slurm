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
OUT_DIR="$SCRATCH/dyna_featuredock_out"
OUT80="$OUT_DIR/pvar_80"; OUT81="$OUT_DIR/pvar_81"
RES="$OUT_DIR/results"; mkdir -p "$RES"
cd "$ROOT/featuredock"

# Optional: warm-start from FeatureDock's pretrained transformer checkpoints.
# Leave empty ("") to train from scratch. If set, matching layers are loaded and
# the shape-changed norm_layer (80->81) is reinitialized automatically.
# Repo ships: results/vit_20/HeavyAtomsite_transformer_20_seed{0,1,10,42,1234}.torch
WARM_START=""   # e.g. "$ROOT/featuredock/results/vit_20/HeavyAtomsite_transformer_20_seed42.torch"
WARM_ARG=""; [ -n "$WARM_START" ] && WARM_ARG="--warm-start $WARM_START"

# 1) CDK2-as-validation split -- 'paper' scope reproduces the repo's
#    make_kfold.py --ignorefile IsRemoved protocol (seed 42) exactly.
python src/curate_dataset/make_cdk2_split.py \
    --datafolder "$OUT81" --datadir "$ROOT/featuredock/data" \
    --cdk2-scope paper --seed 42 \
    --out-train "$OUT_DIR/train_pids.txt" --out-val "$OUT_DIR/val_pids.txt"
echo "--- CDK2 validation ids ---"; cat "$OUT_DIR/val_pids.txt"

# 2) baseline (80 channels)
python src/models/train_dynamics_aware.py \
    --modeltype transformer --feature_per_shell 80 --datafolder "$OUT80" \
    --train-pids "$OUT_DIR/train_pids.txt" --val-pids "$OUT_DIR/val_pids.txt" \
    --outfolder "$RES/baseline80" --modelname baseline80 \
    --steps 1000 --n_structs 16 --lr 1e-3 --save_every 50 --use_gpu $WARM_ARG

# 3) +Dyna-1 (81 channels), identical everything else
python src/models/train_dynamics_aware.py \
    --modeltype transformer --feature_per_shell 81 --datafolder "$OUT81" \
    --train-pids "$OUT_DIR/train_pids.txt" --val-pids "$OUT_DIR/val_pids.txt" \
    --outfolder "$RES/dyna1_81" --modelname dyna1_81 \
    --steps 1000 --n_structs 16 --lr 1e-3 --save_every 50 --use_gpu $WARM_ARG

echo "[train] done. checkpoints + history under $RES/"
