"""
Assign a pocket-level flexibility score to each PDBBind structure and
partition structures into high- / low-flexibility subsets.

Pocket residues = residues with any heavy atom within pocket_cutoff Å of
the ligand centroid (or within the voxel bounding box).

Usage
-----
python flexibility_subset.py \
    --pdbids_file data/pdblist.txt \
    --pdb_dir /data/PDBBind/structures \
    --dyna1_cache dyna_featuredock/cache/dyna1 \
    --out_scores dyna_featuredock/pocket_flexibility.pkl
"""

import os
import pickle
import argparse
import numpy as np
from pathlib import Path


def _ligand_centroid(pdbfile: str) -> np.ndarray | None:
    """Return mean position of HETATM heavy atoms (ligand centroid)."""
    coords = []
    with open(pdbfile, "r") as f:
        for line in f:
            if not line.startswith("HETATM"):
                continue
            atom = line[12:16].strip()
            if atom.startswith("H"):
                continue
            try:
                x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
                coords.append([x, y, z])
            except ValueError:
                pass
    return np.mean(coords, axis=0) if coords else None


def pocket_flexibility(pdbid: str,
                       pdb_dir: str,
                       flexibility: dict,
                       pocket_cutoff: float = 10.0,
                       _pdbfile_override: str | None = None) -> float:
    """
    Mean flexibility of pocket residues (within pocket_cutoff Å of ligand centroid).

    Returns 0.5 (neutral) if ligand or flexibility data is missing.
    """
    if _pdbfile_override:
        pdbfile = _pdbfile_override
    elif pdb_dir:
        pdbfile = os.path.join(pdb_dir, pdbid, f"{pdbid}_protein.pdb")
        if not os.path.exists(pdbfile):
            pdbfile = os.path.join(pdb_dir, f"{pdbid}.pdb")
    else:
        pdbfile = ""
    if not os.path.exists(pdbfile) or not flexibility:
        return 0.5

    centroid = _ligand_centroid(pdbfile)
    if centroid is None:
        return float(np.mean(list(flexibility.values())))

    # collect residues within cutoff
    pocket_flex = []
    with open(pdbfile, "r") as f:
        seen = set()
        for line in f:
            if not line.startswith("ATOM"):
                continue
            atomname = line[12:16].strip()
            if atomname != "CA":
                continue
            chain = line[21]
            resnum = int(line[22:26])
            key = (chain, resnum)
            if key in seen:
                continue
            seen.add(key)
            x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
            dist = np.linalg.norm(np.array([x, y, z]) - centroid)
            if dist <= pocket_cutoff and key in flexibility:
                pocket_flex.append(flexibility[key])

    return float(np.mean(pocket_flex)) if pocket_flex else 0.5


def compute_pocket_scores(pdbids: list,
                          pdb_dir: str,
                          dyna1_cache_dir: str,
                          pocket_cutoff: float = 10.0,
                          verbose: bool = True) -> dict:
    """
    Return {pdbid: mean_pocket_flexibility} for all structures.
    """
    scores = {}
    for i, pid in enumerate(pdbids):
        cache_file = os.path.join(dyna1_cache_dir, f"{pid}.dyna1.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                flex = pickle.load(f)
        else:
            flex = {}
        scores[pid] = pocket_flexibility(pid, pdb_dir, flex, pocket_cutoff)
        if verbose and (i + 1) % 200 == 0:
            print(f"[flex_subset] {i+1}/{len(pdbids)}")
    return scores


def partition_by_flexibility(scores: dict,
                              high_quantile: float = 0.75) -> tuple[list, list]:
    """Return (high_flex_pdbids, low_flex_pdbids)."""
    vals = np.array(list(scores.values()))
    cutoff = np.quantile(vals, high_quantile)
    high = [pid for pid, s in scores.items() if s >= cutoff]
    low  = [pid for pid, s in scores.items() if s <  cutoff]
    print(f"[partition] cutoff={cutoff:.3f}  high={len(high)}  low={len(low)}")
    return high, low


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdbids_file", required=True)
    parser.add_argument("--pdb_dir",     required=True)
    parser.add_argument("--dyna1_cache", required=True)
    parser.add_argument("--out_scores",  required=True)
    parser.add_argument("--pocket_cutoff", type=float, default=10.0)
    parser.add_argument("--high_quantile", type=float, default=0.75)
    args = parser.parse_args()

    with open(args.pdbids_file) as f:
        pdbids = [l.strip() for l in f if l.strip()]

    scores = compute_pocket_scores(pdbids, args.pdb_dir,
                                   args.dyna1_cache, args.pocket_cutoff)
    high, low = partition_by_flexibility(scores, args.high_quantile)

    with open(args.out_scores, "wb") as f:
        pickle.dump({"scores": scores, "high": high, "low": low}, f)
    print(f"Saved pocket flexibility scores to {args.out_scores}")
