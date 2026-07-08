#!/usr/bin/env bash
# Full DynaFeatureDock pipeline
# Assumes:
#   - FeatureDock FEATURE vectors already computed (voxel_dir)
#   - PDB structures in pdb_dir
#   - conda env with biopython, rdkit, torch, sklearn, scipy

set -euo pipefail

PDBIDS_FILE="data/labeled_pdblist.txt"
PDB_DIR="/data/PDBBind/structures"      # each structure: $PDB_DIR/$pdbid/${pdbid}_protein.pdb
VOXEL_DIR="/data/voxels"
DYNA_CACHE="dyna_featuredock/cache/dyna1"
AUGMENTED_DIR="dyna_featuredock/augmented_pvars"
POCKET_SCORES="dyna_featuredock/pocket_flexibility.pkl"
SPLIT_PKL="data/train_val_test_split.pkl"
OUT_DIR="results/dyna_model"
EVAL_CSV="dyna_featuredock/eval_results.csv"

mkdir -p "$DYNA_CACHE" "$AUGMENTED_DIR" "$OUT_DIR"

# ── Step 1: Compute Dyna-1 flexibility scores ──────────────────────────────
echo "=== Step 1: Computing Dyna-1 scores ==="
python - <<'PYEOF'
import sys; sys.path.insert(0, ".")
from dyna_featuredock.dyna1_predictor import batch_flexibility
import os, pickle

with open("data/labeled_pdblist.txt") as f:
    pdbids = [l.strip() for l in f if l.strip()]

results = batch_flexibility(
    pdbids,
    pdb_dir=os.environ.get("PDB_DIR", "/data/PDBBind/structures"),
    cache_dir="dyna_featuredock/cache/dyna1",
    method="auto",   # tries dyna1 package, falls back to B-factors
)
with open("dyna_featuredock/cache/flexibility_all.pkl", "wb") as f:
    pickle.dump(results, f)
print(f"Done: {len(results)} structures")
PYEOF

# ── Step 2: Augment FEATURE vectors with dynamics token ───────────────────
echo "=== Step 2: Augmenting FEATURE vectors ==="
python - <<'PYEOF'
import sys; sys.path.insert(0, ".")
import pickle
from dyna_featuredock.augment_features import batch_augment

with open("data/labeled_pdblist.txt") as f:
    pdbids = [l.strip() for l in f if l.strip()]
with open("dyna_featuredock/cache/flexibility_all.pkl", "rb") as f:
    flex = pickle.load(f)

batch_augment(
    pdbids,
    voxel_dir="$VOXEL_DIR",
    pdb_dir="$PDB_DIR",
    flexibility_dict=flex,
    out_dir="dyna_featuredock/augmented_pvars",
    overwrite=False,
)
PYEOF

# ── Step 3: Compute pocket flexibility scores and partition subsets ────────
echo "=== Step 3: Partitioning high-/low-flex subsets ==="
python dyna_featuredock/flexibility_subset.py \
    --pdbids_file "$PDBIDS_FILE" \
    --pdb_dir     "$PDB_DIR" \
    --dyna1_cache "$DYNA_CACHE" \
    --out_scores  "$POCKET_SCORES"

# ── Step 4: Train DynaFeatureDock ─────────────────────────────────────────
echo "=== Step 4: Training DynaFeatureDock ==="
for SEED in 0 42 1234; do
    python dyna_featuredock/train_dyna.py \
        --dyna_dir    "$AUGMENTED_DIR" \
        --orig_dir    "$VOXEL_DIR" \
        --pdbids_file "$PDBIDS_FILE" \
        --split_pkl   "$SPLIT_PKL" \
        --out_dir     "${OUT_DIR}/seed${SEED}" \
        --seed        "$SEED" \
        --epochs      50 \
        --patience    10 \
        --use_gpu
done

# ── Step 4b: Ablation — train WITHOUT dynamics token ──────────────────────
echo "=== Step 4b: Ablation (no dynamics) ==="
python dyna_featuredock/train_dyna.py \
    --dyna_dir    "$AUGMENTED_DIR" \
    --orig_dir    "$VOXEL_DIR" \
    --pdbids_file "$PDBIDS_FILE" \
    --split_pkl   "$SPLIT_PKL" \
    --out_dir     "${OUT_DIR}/ablation_no_dyna" \
    --no_dynamics \
    --seed        42 \
    --epochs      50 \
    --use_gpu

# ── Step 5: Evaluate on flex subsets ──────────────────────────────────────
echo "=== Step 5: Evaluating on flexibility subsets ==="
python dyna_featuredock/eval_flexibility.py \
    --model_checkpoint "${OUT_DIR}/seed42/best_checkpoint.pt" \
    --model_config     "${OUT_DIR}/seed42/config.torch" \
    --dyna_dir         "$AUGMENTED_DIR" \
    --orig_dir         "$VOXEL_DIR" \
    --pocket_scores    "$POCKET_SCORES" \
    --test_ids_file    data/test_ids.txt \
    --out_csv          "$EVAL_CSV"

echo "Pipeline complete. Results in $EVAL_CSV"
