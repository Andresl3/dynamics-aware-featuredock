#!/bin/bash
#SBATCH --job-name=rmsd_srcabl
#SBATCH --output=/home/mani.na/dyna_logs/rmsd_srcabl_%j.out
#SBATCH --error=/home/mani.na/dyna_logs/rmsd_srcabl_%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:v100-sxm2:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=04:00:00

# ILLUSTRATIVE pose-RMSD eval for SRC + ABL kinases, both regimes.
#
# *** READ THIS BEFORE INTERPRETING THE RESULT ***
#   - n is tiny: SRC = 1 structure (1a1e), ABL1 = 5 (2v7a 3pyy 4twp 4wa9 5hu9).
#     No statistical power -- treat as anecdote, not a head-to-head claim.
#   - These structures were in the TRAINING set (only CDK2's clan was held out),
#     so this measures memorisation, NOT generalisation. It is NOT comparable to
#     the CDK2 held-out result. Label any figure/number "illustrative, train-set".
#
# Same paper settings as CDK2: 500 rotations, top-4 selection, oracle+rank.
set -euo pipefail
mkdir -p /home/mani.na/dyna_logs

# --- batch-safe conda activation (SET ENV_NAME to your real cluster env) ---
ENV_NAME="dynafeat"        # <-- CHANGE to your real cluster env name
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

# SRC (1) + ABL1 (5) pids
printf '1a1e\n2v7a\n3pyy\n4twp\n4wa9\n5hu9\n' > "$R/pids_src_abl.txt"

# --- presence check: which of the 6 actually got preprocessed (pvar+voxels+ligand)? ---
echo "=== presence check (need pvar_81 + voxels + het ligand for each) ==="
ok=0
while read pid; do
  hasv=$( [ -f "$R/pvar_81/${pid}.property.pvar" ] && echo 1 || echo 0 )
  hasx=$( [ -f "$R/voxels/${pid}.voxels.pkl" ] && echo 1 || echo 0 )
  hasl=$( ls "$R/het/${pid}"_ligand.* >/dev/null 2>&1 && echo 1 || echo 0 )
  echo "  $pid : pvar81=$hasv voxels=$hasx ligand=$hasl"
  [ "$hasv$hasx$hasl" = "111" ] && ok=$((ok+1))
done < "$R/pids_src_abl.txt"
echo "  -> $ok/6 fully present"
if [ "$ok" -eq 0 ]; then echo "none present; nothing to do"; exit 1; fi

# ===== from-scratch (5-block) =====
python -u src/models/evaluate_cdk2_rmsd.py \
    --baseline-ckpt "$R/results/baseline80/baseline80_final_params.torch" \
    --baseline-data "$R/pvar_80" \
    --dyna1-ckpt    "$R/results/dyna1_81/dyna1_81_final_params.torch" \
    --dyna1-data    "$R/pvar_81" \
    --voxeldir "$R/voxels" --ligdir "$R/het" \
    --test-pids "$R/pids_src_abl.txt" \
    --outdir "$R/results/src_abl_rmsd_scratch" \
    --nsamples $NS --topk $TK --prob-cutoff 0.5 --seed 0 --nthreads $NT --use_gpu

# ===== warm-start (20-block) =====
python -u src/models/evaluate_cdk2_rmsd.py \
    --baseline-ckpt "$R/results/baseline80_warm/baseline80_warm_final_params.torch" \
    --baseline-data "$R/pvar_80" \
    --dyna1-ckpt    "$R/results/dyna1_81_warm/dyna1_81_warm_final_params.torch" \
    --dyna1-data    "$R/pvar_81" \
    --voxeldir "$R/voxels" --ligdir "$R/het" \
    --test-pids "$R/pids_src_abl.txt" \
    --outdir "$R/results/src_abl_rmsd_warm" \
    --nsamples $NS --topk $TK --prob-cutoff 0.5 --seed 0 --nthreads $NT --use_gpu

echo "=== SRC/ABL from-scratch ==="; cat "$R/results/src_abl_rmsd_scratch/cdk2_rmsd_per_structure.csv"
echo "=== SRC/ABL warm-start ===";  cat "$R/results/src_abl_rmsd_warm/cdk2_rmsd_per_structure.csv"
