"""
Per-residue flexibility scoring using the local Dyna-1 repo (ESM3 backend).

Repo expected at:  dyna_featuredock/Dyna-1-main/Dyna-1-main/
Weights expected:  dyna_featuredock/Dyna-1-main/Dyna-1-main/model/weights/dyna1.pt

Download weights from HuggingFace:
    from huggingface_hub import hf_hub_download
    hf_hub_download(repo_id="gelnesr/Dyna-1", filename="dyna1.pt",
                    local_dir="dyna_featuredock/Dyna-1-main/Dyna-1-main/model/weights/")

ESM3 weights (esm3-sm-open-v1) require HuggingFace access:
    Request access at https://huggingface.co/EvolutionaryScale/esm3-sm-open-v1
    Then: huggingface-cli login   (paste your token)

Priority order for get_flexibility():
1. Cached .dyna1.pkl  → skip recomputation
2. Local Dyna-1 repo  → real µs-ms predictions
3. B-factor proxy     → fast fallback, no ML needed
"""

import os
import sys
import pickle
import tempfile
import subprocess
import numpy as np
from pathlib import Path


# --------------------------------------------------------------------------- #
# Path helpers                                                                 #
# --------------------------------------------------------------------------- #

def _dyna1_root() -> Path:
    """Return path to the Dyna-1-main/Dyna-1-main directory."""
    here = Path(__file__).parent
    return here / "Dyna-1-main" / "Dyna-1-main"


def _weights_exist() -> bool:
    return (_dyna1_root() / "model" / "weights" / "dyna1.pt").exists()


def _python_exe() -> str:
    """Use the same Python that is running this script."""
    return sys.executable


# --------------------------------------------------------------------------- #
# Parse PDB residue numbering for a given chain                               #
# --------------------------------------------------------------------------- #

def _pdb_residue_numbers(pdbfile: str, chain: str = "A") -> list[int]:
    """
    Return the list of residue sequence numbers (in order) for the given chain.
    Only ATOM records, CA atoms, deduplicated.
    """
    resnums = []
    seen = set()
    with open(pdbfile, "r") as f:
        for line in f:
            if not line.startswith("ATOM"):
                continue
            if line[21] != chain:
                continue
            if line[12:16].strip() != "CA":
                continue
            resnum = int(line[22:26])
            if resnum not in seen:
                seen.add(resnum)
                resnums.append(resnum)
    return resnums


# --------------------------------------------------------------------------- #
# Local Dyna-1 inference                                                       #
# --------------------------------------------------------------------------- #

def _run_dyna1_local(pdbfile: str,
                     chain: str = "A",
                     use_pdb_seq: bool = True) -> dict:
    """
    Call dyna1.py as a subprocess from within the Dyna-1 repo directory.
    Returns {(chain, resnum): p_exchange}.
    """
    import pandas as pd

    dyna_root = _dyna1_root()
    script    = dyna_root / "dyna1.py"

    if not script.exists():
        raise FileNotFoundError(f"dyna1.py not found at {script}")
    if not _weights_exist():
        raise FileNotFoundError(
            f"Dyna-1 weights not found at {dyna_root / 'model' / 'weights' / 'dyna1.pt'}.\n"
            "Download with:\n"
            "  from huggingface_hub import hf_hub_download\n"
            f"  hf_hub_download('gelnesr/Dyna-1', 'dyna1.pt', local_dir='{dyna_root / 'model' / 'weights'}')"
        )

    pdb_abs  = str(Path(pdbfile).resolve())
    pdb_name = Path(pdbfile).stem

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            _python_exe(), str(script),
            "--pdb",      pdb_abs,
            "--chain",    chain,
            "--name",     pdb_name,
            "--save_dir", tmpdir,
        ]
        if use_pdb_seq:
            cmd.append("--use_pdb_seq")

        result = subprocess.run(
            cmd,
            cwd=str(dyna_root),          # must run from repo root (relative imports)
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"dyna1.py failed for {pdbfile}:\n{result.stderr[-2000:]}"
            )

        csv_path = Path(tmpdir) / f"{pdb_name}-Dyna1.csv"
        if not csv_path.exists():
            raise FileNotFoundError(
                f"Expected output CSV not found: {csv_path}\n"
                f"stdout: {result.stdout[-500:]}\nstderr: {result.stderr[-500:]}"
            )

        df = pd.read_csv(csv_path)   # columns: position, residue, p_exchange

    # Map 1-indexed positions → actual PDB residue numbers
    resnums = _pdb_residue_numbers(pdbfile, chain)
    scores = {}
    for _, row in df.iterrows():
        idx = int(row["position"]) - 1    # 0-indexed
        if 0 <= idx < len(resnums):
            scores[(chain, resnums[idx])] = float(row["p_exchange"])

    return scores


# --------------------------------------------------------------------------- #
# B-factor fallback                                                            #
# --------------------------------------------------------------------------- #

def _bfactor_proxy(pdbfile: str) -> dict:
    """Normalize backbone Cα B-factors to [0, 1] as a flexibility proxy."""
    bfactors = {}
    with open(pdbfile, "r") as f:
        for line in f:
            if not line.startswith("ATOM"):
                continue
            if line[12:16].strip() != "CA":
                continue
            chain  = line[21]
            resnum = int(line[22:26])
            bfac   = float(line[60:66])
            bfactors[(chain, resnum)] = bfac

    if not bfactors:
        return {}

    vals   = np.array(list(bfactors.values()), dtype=float)
    vmin, vrange = vals.min(), vals.ptp()
    normed = np.zeros_like(vals) if vrange < 1e-6 else (vals - vmin) / vrange
    return {k: float(v) for k, v in zip(bfactors.keys(), normed)}


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #

def get_flexibility(pdbid: str,
                    pdbfile: str,
                    cache_dir: str | None = None,
                    method: str = "auto",
                    chain: str = "A") -> dict:
    """
    Return {(chain, resnum): flexibility_prob [0,1]} for every residue.

    Parameters
    ----------
    pdbid     : PDB identifier (used for cache filename)
    pdbfile   : path to the PDB file
    cache_dir : directory to store/read .dyna1.pkl cache files
    method    : 'dyna1' | 'bfactor' | 'auto'
                auto → tries local Dyna-1, falls back to B-factors
    chain     : which chain to process (default 'A')
    """
    # 1. Try cache
    if cache_dir:
        cached = Path(cache_dir) / f"{pdbid}.dyna1.pkl"
        if cached.exists():
            with open(cached, "rb") as f:
                return pickle.load(f)

    # 2. Run model or proxy
    if method == "dyna1":
        scores = _run_dyna1_local(pdbfile, chain=chain)
    elif method == "bfactor":
        scores = _bfactor_proxy(pdbfile)
    else:   # auto
        try:
            scores = _run_dyna1_local(pdbfile, chain=chain)
        except Exception as e:
            print(f"    [dyna1 fallback → bfactor] {pdbid}: {e.__class__.__name__}: {str(e)[:120]}")
            scores = _bfactor_proxy(pdbfile)

    # 3. Cache result
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        with open(Path(cache_dir) / f"{pdbid}.dyna1.pkl", "wb") as f:
            pickle.dump(scores, f)

    return scores


def batch_flexibility(pdbids: list,
                      pdb_dir: str,
                      cache_dir: str,
                      method: str = "auto",
                      chain: str = "A",
                      verbose: bool = True) -> dict:
    """
    Compute flexibility for a list of PDB IDs.
    pdb_dir layout: $pdb_dir/$pdbid/${pdbid}_protein.pdb
    Returns {pdbid: {(chain, resnum): prob}}.
    """
    results = {}
    for i, pid in enumerate(pdbids):
        pdbfile = os.path.join(pdb_dir, pid, f"{pid}_protein.pdb")
        if not os.path.exists(pdbfile):
            pdbfile = os.path.join(pdb_dir, f"{pid}.pdb")
        if not os.path.exists(pdbfile):
            if verbose:
                print(f"[dyna1] {pid}: PDB not found, skipping")
            continue
        try:
            results[pid] = get_flexibility(pid, pdbfile,
                                           cache_dir=cache_dir,
                                           method=method,
                                           chain=chain)
        except Exception as e:
            if verbose:
                print(f"[dyna1] {pid}: {e}")
        if verbose and (i + 1) % 100 == 0:
            print(f"[dyna1] {i+1}/{len(pdbids)} done")
    return results


# --------------------------------------------------------------------------- #
# Weight download helper                                                       #
# --------------------------------------------------------------------------- #

def download_weights(hf_token: str | None = None) -> str:
    """
    Download dyna1.pt from HuggingFace gelnesr/Dyna-1.
    Returns the path to the downloaded weights file.
    Requires: pip install huggingface_hub
    """
    from huggingface_hub import hf_hub_download  # type: ignore

    dest = _dyna1_root() / "model" / "weights"
    dest.mkdir(parents=True, exist_ok=True)

    path = hf_hub_download(
        repo_id="gelnesr/Dyna-1",
        filename="dyna1.pt",
        local_dir=str(dest),
        token=hf_token,
    )
    print(f"Weights downloaded to: {path}")
    return path
