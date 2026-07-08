"""
Augment FeatureDock FEATURE vectors with Dyna-1 per-residue flexibility scores.

FeatureDock's FEATURE vector layout:
  shape = (N_voxels, num_shells * props_per_shell)  e.g. (N, 6*80) = (N, 480)
  prop[i] = [shell0_prop0, shell0_prop1, ..., shell5_prop79]

We add a dynamics token: for each grid point, compute the mean Dyna-1 flexibility
score of Cα atoms within each of the 6 FEATURE shells (0-1.25, 1.25-2.5, ..., 6.25-7.5 Å).
This yields a (N_voxels, 6) array that we append → (N_voxels, 481).

In the modified transformer, the 481-length vector is reshaped as (81, 6):
  tokens 0-79 → physicochemical properties (each a 6-shell vector)
  token  80   → dynamics token (per-shell flexibility means)

Key design choice: flexibility is shell-resolved, so the transformer can learn
"this grid point has flexible residues in inner shells" vs "outer shells".
"""

import os
import pickle
import numpy as np
from typing import Optional


SHELL_EDGES = np.array([0.0, 1.25, 2.5, 3.75, 5.0, 6.25, 7.5])  # Angstroms


def _parse_residue_coords(pdbfile: str) -> dict:
    """
    Return {(chain, resnum): Cα_xyz} from a PDB file.
    Falls back to first heavy atom if no Cα found.
    """
    ca_coords = {}
    with open(pdbfile, "r") as f:
        for line in f:
            if not line.startswith(("ATOM", "HETATM")):
                continue
            atomname = line[12:16].strip()
            if atomname != "CA":
                continue
            chain = line[21]
            resnum = int(line[22:26])
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
            ca_coords[(chain, resnum)] = np.array([x, y, z])
    return ca_coords


def compute_per_shell_dynamics(voxel_coords: np.ndarray,
                               ca_coords: dict,
                               flexibility: dict,
                               shell_edges: np.ndarray = SHELL_EDGES,
                               fill_value: float = 0.5) -> np.ndarray:
    """
    For each voxel and each shell, compute mean Cα flexibility within that shell.

    Parameters
    ----------
    voxel_coords : (N, 3) grid point coordinates
    ca_coords    : {(chain, resnum): xyz}
    flexibility  : {(chain, resnum): prob}
    shell_edges  : shell boundary distances in Å
    fill_value   : value for shells with no nearby residues

    Returns
    -------
    dyn_token : (N, num_shells) array
    """
    if not ca_coords or not flexibility:
        n_shells = len(shell_edges) - 1
        return np.full((len(voxel_coords), n_shells), fill_value, dtype=np.float32)

    # build arrays of Cα positions and scores for residues present in both
    common_keys = [k for k in ca_coords if k in flexibility]
    if not common_keys:
        n_shells = len(shell_edges) - 1
        return np.full((len(voxel_coords), n_shells), fill_value, dtype=np.float32)

    res_xyz = np.array([ca_coords[k] for k in common_keys], dtype=np.float32)  # (R, 3)
    res_flex = np.array([flexibility[k] for k in common_keys], dtype=np.float32)  # (R,)

    n_voxels = len(voxel_coords)
    n_shells = len(shell_edges) - 1
    dyn_token = np.full((n_voxels, n_shells), fill_value, dtype=np.float32)

    # batch voxels to avoid OOM (at most ~5000 at a time)
    batch = 2000
    for start in range(0, n_voxels, batch):
        end = min(start + batch, n_voxels)
        v = voxel_coords[start:end]                          # (B, 3)
        # pairwise distances: (B, R)
        diff = v[:, None, :] - res_xyz[None, :, :]          # (B, R, 3)
        dist = np.linalg.norm(diff, axis=-1)                 # (B, R)
        for s in range(n_shells):
            lo, hi = shell_edges[s], shell_edges[s + 1]
            mask = (dist >= lo) & (dist < hi)                # (B, R)
            counts = mask.sum(axis=1)                        # (B,)
            # sum flex scores for residues in shell
            vals = (mask * res_flex[None, :]).sum(axis=1)    # (B,)
            has_res = counts > 0
            dyn_token[start:end, s] = np.where(
                has_res, vals / np.maximum(counts, 1), fill_value
            )

    return dyn_token


def augment_pvar(pvarfile: str,
                 voxelfile: str,
                 pdbfile: str,
                 flexibility: dict,
                 out_pvarfile: Optional[str] = None) -> np.ndarray:
    """
    Load a .property.pvar, append the dynamics token, save as *_dyna.pvar.

    Parameters
    ----------
    pvarfile    : original (N, 480) FEATURE pickle
    voxelfile   : (N, 3) voxel coordinate pickle
    pdbfile     : protein PDB (for Cα extraction)
    flexibility : {(chain, resnum): prob}
    out_pvarfile: output path; if None, returns array without saving

    Returns
    -------
    augmented   : (N, 481) array  [480 FEATURE props + 6-shell dyn token]
    """
    with open(pvarfile, "rb") as f:
        prop = pickle.load(f)                 # (N, 480)
    with open(voxelfile, "rb") as f:
        voxels = pickle.load(f)               # (N, 3)

    ca_coords = _parse_residue_coords(pdbfile)
    dyn_token = compute_per_shell_dynamics(voxels, ca_coords, flexibility)  # (N, 6)
    augmented = np.concatenate([prop, dyn_token], axis=1).astype(np.float32)  # (N, 486)

    if out_pvarfile:
        with open(out_pvarfile, "wb") as f:
            pickle.dump(augmented, f)

    return augmented


def batch_augment(pdbids: list,
                  voxel_dir: str,
                  pdb_dir: str,
                  flexibility_dict: dict,
                  out_dir: str,
                  overwrite: bool = False,
                  verbose: bool = True):
    """
    Augment all .property.pvar files in voxel_dir for the given pdbids.

    flexibility_dict : {pdbid: {(chain, resnum): prob}}
    out_dir          : directory to write *_dyna.pvar files
    """
    os.makedirs(out_dir, exist_ok=True)
    failed = []
    for i, pid in enumerate(pdbids):
        out_path = os.path.join(out_dir, f"{pid}.dyna.pvar")
        if not overwrite and os.path.exists(out_path):
            continue

        pvarfile = os.path.join(voxel_dir, f"{pid}.property.pvar")
        voxelfile = os.path.join(voxel_dir, f"{pid}.voxels.pkl")
        pdbfile = os.path.join(pdb_dir, pid, f"{pid}_protein.pdb")
        if not os.path.exists(pdbfile):
            pdbfile = os.path.join(pdb_dir, f"{pid}.pdb")

        if not all(os.path.exists(p) for p in [pvarfile, voxelfile, pdbfile]):
            failed.append(pid)
            continue

        flex = flexibility_dict.get(pid, {})
        try:
            augment_pvar(pvarfile, voxelfile, pdbfile, flex, out_pvarfile=out_path)
        except Exception as e:
            if verbose:
                print(f"[augment] {pid}: {e}")
            failed.append(pid)

        if verbose and (i + 1) % 200 == 0:
            print(f"[augment] {i+1}/{len(pdbids)} done")

    if failed:
        print(f"[augment] {len(failed)} structures failed: {failed[:10]}...")
