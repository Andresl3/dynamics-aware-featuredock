#!/bin/bash
# setup_env.sh -- one-time environment build on the HPC login node.
# Creates a conda env with the full dynamics-aware-FeatureDock stack, clones the
# two tool repos, overlays our patched code, unpacks FEATURE, and downloads the
# Dyna-1 weights. Run once from the repo root:  bash hpc/setup_env.sh
set -euo pipefail

ENV_NAME="${ENV_NAME:-dynafeat}"
ROOT="${ROOT:-$PWD}"                 # run from the cloned dynamics-aware-featuredock repo
echo "[setup] repo root: $ROOT   env: $ENV_NAME"

# ---- 1. conda env (Python 3.11) ----
# module load anaconda3   # <-- uncomment / adjust for your cluster
conda create -y -n "$ENV_NAME" python=3.11
# shellcheck disable=SC1091
source activate "$ENV_NAME" 2>/dev/null || conda activate "$ENV_NAME"

# ---- 2. GPU PyTorch. PICK THE CUDA BUILD MATCHING YOUR GPU ----
# You MUST match the torch CUDA build to the GPU on the node you will run on.
# First find your GPU's compute capability:
#     nvidia-smi
#     python -c "import torch; print(torch.cuda.get_device_capability(0))"  # after a torch is installed
#
# Then pick the wheel (uncomment ONE line below):
#
#   Volta/Turing   (V100 sm_70, T4 sm_75):              cu118 or cu121
#   Ampere         (A100 sm_80, RTX 30xx sm_86):        cu121 or cu124
#   Hopper         (H100 sm_90):                        cu124 (or cu121)
#   Blackwell      (RTX PRO 6000 / RTX 50-series):      cu128
#       NOTE: Blackwell needs a cu128 (or newer) wheel; older cu121/cu124 wheels
#       lack the Blackwell kernels and fail with "no kernel image is available
#       for execution on the device". The exact sm_1xx capability for a given
#       Blackwell card varies by SKU (reports differ, e.g. sm_120 vs sm_122) --
#       don't hard-code a number; just install cu128 and let the VERIFY step below
#       print what actually loaded.
#
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128   # Blackwell
# CPU-only fallback: pip install torch torchvision torchaudio
#
# VERIFY: is_available() is NOT enough -- launch a real kernel. If this errors
# with "no kernel image", your GPU's capability isn't in the installed build:
python -c "import torch; print('torch', torch.__version__, '| built for CUDA', torch.version.cuda); \
print('arch list:', torch.cuda.get_arch_list()); \
print('this GPU:', torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0)); \
x=torch.randn(1024,1024,device='cuda'); print('gpu matmul ok:', float((x@x).sum()))" \
  || echo "[setup] WARN: GPU check failed -- pick a torch CUDA build that supports your card's capability"

# ---- 3. scientific + pipeline deps (numpy pinned <2 for Dyna-1/biotite) ----
pip install "numpy<2" scipy pandas scikit-learn biopython tqdm
pip install rdkit prolif MDAnalysis mdtraj gemmi
pip install pymol-open-source || echo "[setup] WARN: pip pymol failed; try 'conda install -c conda-forge pymol-open-source'"
pip install torcheval msgpack msgpack-numpy cloudpickle tenacity
pip install "transformers<4.47.0" "huggingface_hub[cli]" fair-esm "biotite==0.41.2"

# ---- 4. clone the two tool repos next to this one ----
cd "$ROOT"
[ -d featuredock ] || git clone https://github.com/xuhuihuang/featuredock.git
[ -d Dyna-1 ]      || git clone https://github.com/WaymentSteeleLab/Dyna-1.git
# Dyna-1's own requirements (minus torch, already installed above)
grep -v -E "^torch" Dyna-1/requirements.txt > /tmp/dyna1_reqs.txt 2>/dev/null || true
pip install -r /tmp/dyna1_reqs.txt 2>/dev/null || true

# ---- 5. overlay OUR patched code into the cloned FeatureDock/Dyna-1 ----
cp code/curate_dataset/featurize_dyna1_channel.py    featuredock/src/curate_dataset/
cp code/curate_dataset/make_cdk2_split.py            featuredock/src/curate_dataset/
cp code/curate_dataset/create_voxels_and_landmarks.py featuredock/src/curate_dataset/
cp code/models/train_dynamics_aware.py               featuredock/src/models/
cp code/models/parse_config.py                       featuredock/src/models/
cp code/dyna1/precompute_dyna1.py                    Dyna-1/
echo "[setup] patched code overlaid"

# ---- 6. unpack FEATURE + make binaries executable ----
cd featuredock/src/utils
unzip -o -q feature-3.1.0.zip -d ../
FP="$ROOT/featuredock/src/feature-3.1.0"
chmod +x "$FP/src/featurize" "$FP/bin/featurize" "$FP/bin/buildmodel" "$FP/bin/scoreit" 2>/dev/null || true
chmod +x "$ROOT/featuredock/src/utils/dssp" 2>/dev/null || true
cd "$ROOT"
"$FP/src/featurize" 2>&1 | head -2 || true   # should print usage, NOT "Permission denied"

# ---- 7. Dyna-1 ESM-2 weights ----
cd Dyna-1 && mkdir -p model/weights
huggingface-cli download gelnesr/Dyna-1 --local-dir model/weights/ | tail -2
cd "$ROOT"

echo "[setup] DONE. Activate with: conda activate $ENV_NAME"
echo "[setup] Then submit:  sbatch hpc/run_preprocess.slurm"
