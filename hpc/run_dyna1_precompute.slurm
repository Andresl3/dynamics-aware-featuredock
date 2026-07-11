#!/bin/bash
#SBATCH --job-name=dyna1_precompute
#SBATCH --output=logs/dyna1_%j.out
#SBATCH --error=logs/dyna1_%j.err
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --ntasks=1
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --partition=multigpu

# Precompute Dyna-1 p_exchange CSVs for the ENTIRE refined set, ONCE.
# Loads the ESM-2 model a single time and loops all refined structures, writing
# one <pid>.csv per protein. Resumable: existing CSVs are skipped. After this,
# preprocess.py reuses these CSVs instead of reloading the 205 MB model per
# structure -- the Dyna-1 stage becomes a cache read.
set -euo pipefail
mkdir -p logs

# --- environment ---
# module load anaconda3            # <-- uncomment, match `module avail anaconda`
source activate "${ENV_NAME:-dynafeat}" 2>/dev/null || conda activate "${ENV_NAME:-dynafeat}"

# --- paths (EDIT to match your cluster) ---
ROOT="/scratch/mani.na/dynamics-aware-featuredock"
PDBBIND_DIR="/scratch/mani.na/dynamics-aware-featuredock/PDBbind_v2020/P-L"
OUT_DIR="/scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out"
SAVE_DIR="$OUT_DIR/dyna1_csv"          # preprocess.py reads Dyna-1 CSVs from here

echo "host: $(hostname); GPU: $(nvidia-smi -L 2>/dev/null | head -1)"

python "$ROOT/Dyna-1/precompute_dyna1.py" \
    --pdbbind-dir  "$PDBBIND_DIR" \
    --refined-list "$ROOT/featuredock/data/pdblist.txt" \
    --dyna1-root   "$ROOT/Dyna-1" \
    --save-dir     "$SAVE_DIR"

echo "[dyna1] done. CSVs in $SAVE_DIR"
ls "$SAVE_DIR" | wc -l
