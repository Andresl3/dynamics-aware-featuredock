"""
featurize_dyna1_channel.py
==========================
Augmentation (1) of Dynamics-aware FeatureDock.

Append a per-shell Dyna-1 micro-millisecond MOTION channel to FeatureDock's
grid-point FEATURE tensor, taking each pocket from 6 x 80 -> 6 x 81 features.

FeatureDock describes every grid point with the Altman FEATURE vector: 6
concentric shells (each `width` = 1.25 A thick) centred on the grid point, and
80 physicochemical properties aggregated per shell -> a (N, 6*80) = (N, 480)
tensor stored as `<pid>.property.pvar`.

This module computes ONE extra property per shell -- the aggregated Dyna-1
`p_exchange` (probability a residue undergoes us-ms conformational exchange) of
the protein residues whose atoms fall inside that shell -- and inserts it as the
81st property of each shell, giving (N, 6*81) = (N, 486). The insertion mirrors
FEATURE's own shell aggregation so the new channel is on equal footing with the
existing 80.

Layout convention (matches FeatureDock's model reshape
`feature_batch.view(-1, num_shells, feature_per_shell)`):
    flat index = shell * feature_per_shell + property
so for each shell we append the motion value AFTER its 80 native properties.

Inputs
------
--pdb        : protein structure (PDB/mmCIF) used to build the FEATURE file
--voxelfile  : <pid>.voxels.pkl  -- (N, 3) grid-point coordinates
--pvarfile   : <pid>.property.pvar -- (N, 480) native FEATURE tensor
--dyna1csv   : Dyna-1 output CSV with columns [position, residue, p_exchange]
--out        : output path for the extended (N, 486) tensor (.pkl)

The Dyna-1 CSV is indexed by sequence position (1..L). We align it to structure
residues by author residue order within the modelled chain(s); a --chain filter
and an explicit --seq-offset are provided for cases where the numbering differs.

Runs on CPU; no GPU needed. Depends only on numpy, scipy, biotite (all in env).
"""
import os
import sys
import pickle
import argparse
import numpy as np
import pandas as pd
from scipy import spatial

NUM_SHELL_DEFAULT = 6
WIDTH_DEFAULT = 1.25
FEATURE_PER_SHELL = 80  # native Altman FEATURE properties per shell


def load_structure_atoms(pdb_path, chain=None):
    """Return (atom_xyz (M,3), res_key_per_atom (M,)) for protein atoms.

    res_key is a stable per-residue identifier (chain, res_id, ins_code) so we
    can group atoms into residues and align to the Dyna-1 per-residue table.
    Uses Biopython (dependency of all three Hackathon tools); reads the first
    model and standard amino-acid residues only (drops HETATM waters/ligands).
    """
    from Bio.PDB import PDBParser, MMCIFParser
    from Bio.PDB.Polypeptide import is_aa

    is_cif = pdb_path.lower().endswith((".cif", ".mmcif"))
    parser = MMCIFParser(QUIET=True) if is_cif else PDBParser(QUIET=True)
    structure = parser.get_structure("s", pdb_path)
    model = next(structure.get_models())  # first model only

    xyz = []
    res_keys = []
    for ch in model:
        if chain is not None and ch.id != chain:
            continue
        for res in ch:
            if not is_aa(res, standard=True):
                continue  # skip water/ligand/non-standard
            hetflag, resseq, icode = res.id
            if hetflag.strip():  # skip HETATM residues
                continue
            key = f"{ch.id}|{resseq}|{icode.strip()}"
            for atom in res:
                xyz.append(atom.coord)
                res_keys.append(key)
    if not xyz:
        raise ValueError(f"No protein atoms found in {pdb_path}"
                         + (f" for chain {chain}" if chain else ""))
    return np.asarray(xyz, dtype=np.float64), np.asarray(res_keys)


def residue_order(res_keys):
    """Ordered unique residue keys, preserving first-appearance order."""
    seen = {}
    order = []
    for k in res_keys:
        if k not in seen:
            seen[k] = len(order)
            order.append(k)
    return order, seen


def build_residue_pexchange(dyna1_csv, res_order, seq_offset=0):
    """Map Dyna-1 per-residue p_exchange onto structure residues by order.

    Dyna-1 rows are sequence positions 1..L. We align position i (1-based) to
    the i-th modelled residue (plus optional seq_offset). Residues without a
    Dyna-1 value (e.g. unmodelled gaps beyond L) get NaN and are ignored in
    aggregation.
    """
    df = pd.read_csv(dyna1_csv)
    needed = {"position", "p_exchange"}
    if not needed.issubset(df.columns):
        raise ValueError(f"{dyna1_csv} must have columns {needed}, got {list(df.columns)}")
    p_by_pos = dict(zip(df["position"].astype(int), df["p_exchange"].astype(float)))
    res_p = np.full(len(res_order), np.nan, dtype=np.float64)
    for idx in range(len(res_order)):
        pos = idx + 1 + seq_offset  # 1-based Dyna-1 position for this residue
        if pos in p_by_pos:
            res_p[idx] = p_by_pos[pos]
    n_mapped = np.sum(~np.isnan(res_p))
    return res_p, n_mapped


def compute_motion_channel(voxels, atom_xyz, atom_res_idx, res_p,
                           num_shell=NUM_SHELL_DEFAULT, width=WIDTH_DEFAULT,
                           agg="mean"):
    """For each voxel and shell, aggregate p_exchange of residues in that shell.

    Parameters
    ----------
    voxels      : (N,3) grid points
    atom_xyz    : (M,3) protein atom coords
    atom_res_idx: (M,) index into res_p for each atom's residue
    res_p       : (R,) per-residue p_exchange (may contain NaN)
    Returns
    -------
    motion : (N, num_shell) aggregated motion per shell (NaN-shells -> 0.0)
    """
    N = voxels.shape[0]
    motion = np.zeros((N, num_shell), dtype=np.float64)
    # radial shell edges: shell k covers [k*width, (k+1)*width)
    max_r = num_shell * width
    tree = spatial.cKDTree(atom_xyz)
    # per-atom p_exchange (NaN where residue unmapped)
    atom_p = res_p[atom_res_idx]
    for i in range(N):
        # atoms within the outermost shell of this voxel
        idxs = tree.query_ball_point(voxels[i], r=max_r)
        if not idxs:
            continue
        idxs = np.asarray(idxs)
        d = np.linalg.norm(atom_xyz[idxs] - voxels[i], axis=1)
        shell_id = np.floor(d / width).astype(int)
        shell_id = np.clip(shell_id, 0, num_shell - 1)
        pv = atom_p[idxs]
        for k in range(num_shell):
            sel = (shell_id == k) & ~np.isnan(pv)
            if np.any(sel):
                vals = pv[sel]
                motion[i, k] = float(np.mean(vals)) if agg == "mean" else float(np.max(vals))
    return motion


def insert_channel(pvar, motion, num_shell=NUM_SHELL_DEFAULT,
                   feature_per_shell=FEATURE_PER_SHELL):
    """Interleave the motion column into each shell: (N,480)->(N,486).

    Native flat layout is shell-major: [s0f0..s0f79, s1f0..s1f79, ...].
    We rebuild as [s0f0..s0f79, s0_motion, s1f0..s1f79, s1_motion, ...].
    """
    pvar = np.asarray(pvar, dtype=np.float64)
    N = pvar.shape[0]
    assert pvar.shape[1] == num_shell * feature_per_shell, \
        f"expected {num_shell*feature_per_shell} cols, got {pvar.shape[1]}"
    assert motion.shape == (N, num_shell), f"motion shape {motion.shape} != {(N, num_shell)}"
    blocks = []
    for k in range(num_shell):
        native = pvar[:, k * feature_per_shell:(k + 1) * feature_per_shell]
        blocks.append(native)
        blocks.append(motion[:, k:k + 1])  # the 81st property of this shell
    out = np.concatenate(blocks, axis=1)
    assert out.shape == (N, num_shell * (feature_per_shell + 1))
    return out


def main():
    ap = argparse.ArgumentParser(description="Append Dyna-1 motion channel (6x80 -> 6x81).")
    ap.add_argument("--pdb", required=True, help="protein structure PDB/mmCIF")
    ap.add_argument("--voxelfile", required=True, help="<pid>.voxels.pkl (N,3)")
    ap.add_argument("--pvarfile", required=True, help="<pid>.property.pvar (N,480)")
    ap.add_argument("--dyna1csv", required=True, help="Dyna-1 CSV [position,residue,p_exchange]")
    ap.add_argument("--out", required=True, help="output .pkl for (N,486) tensor")
    ap.add_argument("--chain", default=None, help="restrict to this chain id")
    ap.add_argument("--seq-offset", type=int, default=0,
                    help="add to residue index when aligning to Dyna-1 position")
    ap.add_argument("--num-shell", type=int, default=NUM_SHELL_DEFAULT)
    ap.add_argument("--width", type=float, default=WIDTH_DEFAULT)
    ap.add_argument("--agg", choices=["mean", "max"], default="mean")
    args = ap.parse_args()

    with open(args.voxelfile, "rb") as f:
        voxels = np.asarray(pickle.load(f), dtype=np.float64)
    with open(args.pvarfile, "rb") as f:
        pvar = np.asarray(pickle.load(f), dtype=np.float64)

    atom_xyz, atom_res_keys = load_structure_atoms(args.pdb, chain=args.chain)
    res_order, key2idx = residue_order(atom_res_keys)
    atom_res_idx = np.array([key2idx[k] for k in atom_res_keys])
    res_p, n_mapped = build_residue_pexchange(args.dyna1csv, res_order, args.seq_offset)
    print(f"[dyna1-channel] residues={len(res_order)} mapped_to_pexchange={n_mapped} "
          f"atoms={len(atom_xyz)} voxels={len(voxels)}")

    motion = compute_motion_channel(voxels, atom_xyz, atom_res_idx, res_p,
                                    num_shell=args.num_shell, width=args.width, agg=args.agg)
    out = insert_channel(pvar, motion, num_shell=args.num_shell,
                         feature_per_shell=FEATURE_PER_SHELL)
    with open(args.out, "wb") as f:
        pickle.dump(out, f)
    covered = float(np.mean(np.any(motion > 0, axis=1)))
    print(f"[dyna1-channel] wrote {args.out} shape={out.shape} "
          f"motion range=[{motion.min():.3f},{motion.max():.3f}] "
          f"voxels_with_motion={covered:.1%}")


if __name__ == "__main__":
    main()
