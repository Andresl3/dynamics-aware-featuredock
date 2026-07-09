#!/bin/bash
#SBATCH --job-name=dynafeat_prep
#SBATCH --output=logs/prep_%A_%a.out
#SBATCH --error=logs/prep_%A_%a.err
#SBATCH --array=1-10            # 10 shards; each task does 1/10 of the dataset
#SBATCH --gres=gpu:1           # Dyna-1 (ESM-2) inference uses the GPU
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=12:00:00
# ---- EDIT THESE for your cluster (partition/account) ----
###SBATCH --partition=gpu
###SBATCH --account=your_alloc

# Preprocess PDBBind -> 6x80 + 6x81 tensors + labels, sharded across the array.
# Each array task processes shard SLURM_ARRAY_TASK_ID / SLURM_ARRAY_TASK_COUNT.
set -euo pipefail
mkdir -p logs

# --- environment ---
# module load anaconda3 cuda      # <-- adjust for your cluster
source activate "${ENV_NAME:-dynafeat}" 2>/dev/null || conda activate "${ENV_NAME:-dynafeat}"

# --- paths (EDIT) ---
ROOT="$HOME/dynamics-aware-featuredock"
PDBBIND_DIR="$DATA/PDBbind_v2020/P-L"     # your extracted PDBBind (flat or P-L/year/pid)
OUT_DIR="$SCRATCH/dyna_featuredock_out"   # big; put on scratch/fast storage

N=$SLURM_ARRAY_TASK_COUNT
K=$SLURM_ARRAY_TASK_ID
echo "shard $K/$N on $(hostname); GPU: $(nvidia-smi -L 2>/dev/null | head -1)"

python "$ROOT/hpc/preprocess.py" \
    --pdbbind-dir "$PDBBIND_DIR" \
    --featuredock "$ROOT/featuredock" \
    --dyna1-root  "$ROOT/Dyna-1" \
    --out-dir     "$OUT_DIR" \
    --refined-only \
    --shard "$K/$N"

# Optional smoke test first: add  --limit 30  and set --array=1-1
