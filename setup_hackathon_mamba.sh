#!/bin/bash
# ==========================================================================
# setup_hackathon_mamba.sh
# Recreate the "Hackathon" environment in YOUR homebrew micromamba,
# with all three tools (FEATUREdock, Dyna-1, protpardelle-1c) installed.
#
# Run this in YOUR terminal (NOT inside Claude Science):
#     bash setup_hackathon_mamba.sh
#
# Single modern stack: Python 3.11 + current PyTorch (as chosen earlier).
# ==========================================================================
set -euo pipefail

# --- 0. config ------------------------------------------------------------
ENV_NAME="Hackathon"
CODE_DIR="$HOME/Hackathon"          # stable location for the 3 repos (edit here)
MM="micromamba"                     # your homebrew micromamba

# --- 1. clone the three repos into one folder -----------------------------
mkdir -p "$CODE_DIR"
cd "$CODE_DIR"
[ -d featuredock ]      || git clone https://github.com/xuhuihuang/featuredock.git
[ -d Dyna-1 ]           || git clone https://github.com/WaymentSteeleLab/Dyna-1.git
[ -d protpardelle-1c ]  || git clone https://github.com/ProteinDesignLab/protpardelle-1c.git

# --- 2. create the env with conda-level packages --------------------------
# (torch + the deps that must be prebuilt binaries: prody, pymol, dssp)
"$MM" create -y -n "$ENV_NAME" -c pytorch -c conda-forge \
    python=3.11 pytorch torchvision torchaudio \
    numpy scipy pandas prody pymol-open-source dssp

# activate for the pip steps
eval "$("$MM" shell hook --shell bash)"
"$MM" activate "$ENV_NAME"

# --- 3. protpardelle-1c : editable install (has pyproject.toml) -----------
#   prody already came from conda, so its source build is skipped
cd "$CODE_DIR/protpardelle-1c"
pip install -e .
# hydra-core is a declared protpardelle dep; install explicitly so the
# sanity check below never depends on transitive resolution
pip install --prefer-binary hydra-core

# --- 4. Dyna-1 : no build file -> install deps, run in place --------------
#   torch* and torchtext removed (torchtext is unused + breaks on modern torch)
pip install --prefer-binary \
    "transformers<4.47.0" ipython einops "biotite==0.41.2" msgpack-numpy \
    biopython scikit-learn brotli attrs pandas cloudpathlib tenacity \
    wandb torcheval mdtraj MDAnalysis

# --- 5. FEATUREdock : no build file -> install its imports, run in place ---
pip install --prefer-binary rdkit prolif networkx wget pyparsing \
    importlib-resources zipp

# --- 6. sanity check ------------------------------------------------------
python - <<'PY'
import importlib
mods = ["protpardelle","prody","hydra","biotite","transformers","torch",
        "torcheval","mdtraj","MDAnalysis","msgpack_numpy","cloudpathlib","wandb",
        "rdkit","prolif","networkx","pymol","wget","sklearn"]
bad = []
for m in mods:
    try: importlib.import_module(m)
    except Exception as e: bad.append((m, str(e)[:60]))
print("All import OK" if not bad else "FAILED: "+str(bad))
PY

echo ""
echo "Done. Repos are in: $CODE_DIR"
echo "Use it any time with:   micromamba activate $ENV_NAME"
