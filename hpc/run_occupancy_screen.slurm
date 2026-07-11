#!/bin/bash
#SBATCH --job-name=occ_screen
#SBATCH --output=/home/mani.na/dyna_logs/occ_screen_%j.out
#SBATCH --error=/home/mani.na/dyna_logs/occ_screen_%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:v100-sxm2:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00

# OCCUPANCY screen for 3 dynamics-tiered targets, BOTH regimes.
#   p38a   (n=26)  dynamics-rich, CDK2-matched power  -> effect EXPECTED if any
#   hsp90a (n=94)  high power, lid/open-closed motion  -> can detect small effect
#   ca2    (n=292) rigid control, little dynamics      -> should show NO effect
#
# *** ILLUSTRATIVE, TRAIN-SET ***  All three targets were in the TRAINING set
# (only CDK2's clan was held out), so this measures memorisation, NOT
# generalisation, and is NOT directly comparable to the CDK2 held-out result.
# A NULL here does NOT confirm "no effect" (both arms sit near the train ceiling);
# a clear POSITIVE here is a real lead worth a held-out retrain. Label every
# number "illustrative, train-set".
#
# Occupancy (one forward pass/structure) is cheap -> runs at FULL n. Posing/RMSD
# is the expensive follow-up, only if a target lights up here.
set -euo pipefail
mkdir -p /home/mani.na/dyna_logs

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
PIDDIR=/scratch/mani.na/dynamics-aware-featuredock/hpc/target_pids   # upload the 3 *_pids.txt here

for TGT in p38a hsp90a ca2; do
  echo ""; echo "############ OCCUPANCY: $TGT ############"
  PIDS="$PIDDIR/${TGT}_pids.txt"
  if [ ! -f "$PIDS" ]; then echo "MISSING pid list: $PIDS"; continue; fi
  echo "[$TGT] n=$(wc -l < "$PIDS") structures"

  # from-scratch models
  python -u src/models/evaluate_cdk2.py \
      --baseline-ckpt "$R/results/baseline80/baseline80_final_params.torch" \
      --baseline-data "$R/pvar_80" \
      --dyna1-ckpt    "$R/results/dyna1_81/dyna1_81_final_params.torch" \
      --dyna1-data    "$R/pvar_81" \
      --test-pids "$PIDS" \
      --outdir "$R/results/occ_${TGT}_scratch" --use_gpu

  # warm-start models
  python -u src/models/evaluate_cdk2.py \
      --baseline-ckpt "$R/results/baseline80_warm/baseline80_warm_final_params.torch" \
      --baseline-data "$R/pvar_80" \
      --dyna1-ckpt    "$R/results/dyna1_81_warm/dyna1_81_warm_final_params.torch" \
      --dyna1-data    "$R/pvar_81" \
      --test-pids "$PIDS" \
      --outdir "$R/results/occ_${TGT}_warm" --use_gpu
done

echo ""; echo "############ SUMMARY (all targets, both regimes) ############"
for TGT in p38a hsp90a ca2; do
  for REG in scratch warm; do
    f="$R/results/occ_${TGT}_${REG}/cdk2_summary.csv"
    echo "--- $TGT / $REG ---"; [ -f "$f" ] && cat "$f" || echo "(missing)"
  done
done
