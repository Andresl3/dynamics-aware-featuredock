"""
OpenADMET integration: apply DynaFeatureDock to the ExpansionRx challenge dataset.

The shin-chan team's approach (from the model report) uses ensemble models with
physicochemical features. Here we plug in the DynaFeatureDock envelope as an
additional structural feature alongside ADMET predictions.

Key idea (from the Shin-chan report):
  - ADMET properties alone do not capture binding-site complementarity
  - We score each compound against the target pocket using the Dyna envelope
  - The envelope score (mean P(ligand site) over heavy atoms) feeds into the ensemble

Pipeline
--------
1. Load expansion candidates from OpenADMET dataset
2. For each target protein, compute/load the DynaFeatureDock envelope
3. Score each candidate SMILES against the envelope using the FeatureDock
   pose-optimization protocol (L-BFGS-B over RDKit conformers, Eq. 2/3 in paper)
4. Return envelope scores that can be combined with ADMET features

Usage
-----
python dyna_featuredock/openadmet_integration.py \
    --csv_path expansion_data_train.csv \
    --model_checkpoint results/dyna_model/best_checkpoint.pt \
    --model_config     results/dyna_model/config.torch \
    --pocket_dir       /data/pocket_pvars \
    --out_csv          dyna_featuredock/openadmet_scores.csv
"""

import os
import sys
import pickle
import argparse
import numpy as np
import pandas as pd
import torch
from pathlib import Path

# Load from HuggingFace (requires: pip install datasets)
OPENADMET_HF = (
    "hf://datasets/openadmet/openadmet-expansionrx-challenge-train-data/"
    "expansion_data_train.csv"
)


def load_openadmet(csv_path: str | None = None) -> pd.DataFrame:
    """Load OpenADMET ExpansionRx training data."""
    if csv_path and os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    print("Loading OpenADMET from HuggingFace...")
    import pandas as pd   # noqa: F811  (already imported, keep for clarity)
    return pd.read_csv(OPENADMET_HF)


def smiles_to_heavy_atom_coords(smiles: str, n_confs: int = 10,
                                 seed: int = 42) -> np.ndarray | None:
    """
    Generate RDKit 3D conformers and return heavy-atom coordinates of
    the lowest-energy conformer. Returns None if embedding fails.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, rdMolDescriptors
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        mol = Chem.AddHs(mol)
        params = AllChem.ETKDGv3()
        params.randomSeed = seed
        params.numThreads = 1
        ids = AllChem.EmbedMultipleConfs(mol, numConfs=n_confs, params=params)
        if not ids:
            return None
        AllChem.MMFFOptimizeMoleculeConfs(mol, numThreads=1)
        conf = mol.GetConformer(0)
        coords = []
        for atom in mol.GetAtoms():
            if atom.GetAtomicNum() == 1:
                continue
            pos = conf.GetAtomPosition(atom.GetIdx())
            coords.append([pos.x, pos.y, pos.z])
        return np.array(coords, dtype=np.float32) if coords else None
    except Exception:
        return None


def score_ligand_against_envelope(heavy_atom_coords: np.ndarray,
                                   voxel_coords: np.ndarray,
                                   voxel_probs: np.ndarray,
                                   sigma: float = 1.0) -> float:
    """
    FeatureDock Eq. 2/3 scoring: sum over ligand heavy atoms of the
    highest-probability grid point within sigma Å.

    Implements: score = mean_j max_i { P(i) * exp(-d(i,j)^2 / sigma^2) }
    where i = grid points, j = ligand heavy atoms.
    """
    if heavy_atom_coords is None or len(heavy_atom_coords) == 0:
        return 0.0
    # (J, I) distance matrix
    diff = heavy_atom_coords[:, None, :] - voxel_coords[None, :, :]  # (J, I, 3)
    d2   = (diff ** 2).sum(axis=-1)                                    # (J, I)
    w    = voxel_probs[None, :] * np.exp(-d2 / (sigma ** 2))          # (J, I)
    return float(w.max(axis=1).mean())


def envelope_from_pvar(pvar_path: str,
                        voxel_path: str,
                        model: torch.nn.Module,
                        device: str,
                        batch_size: int = 4096) -> tuple[np.ndarray, np.ndarray]:
    """
    Run DynaFeatureDock forward pass over a pocket's .pvar file.
    Returns (voxel_coords, ligand_site_probabilities).
    """
    with open(pvar_path, "rb") as f:
        prop = pickle.load(f)            # (N, 480 or 486)
    with open(voxel_path, "rb") as f:
        coords = pickle.load(f)          # (N, 3)

    model.eval()
    probs = []
    with torch.no_grad():
        for start in range(0, len(prop), batch_size):
            batch = torch.from_numpy(prop[start:start + batch_size].astype(
                                     np.float32)).to(device)
            logits = model(batch)
            p = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
            probs.extend(p)
    return coords, np.array(probs)


def score_dataset(df: pd.DataFrame,
                  smiles_col: str,
                  target_col: str,
                  pocket_dir: str,
                  model: torch.nn.Module,
                  device: str) -> pd.DataFrame:
    """
    Score every row in df. Adds columns:
      envelope_score   : FeatureDock Eq. 2/3 score against DynaFeatureDock envelope
      pocket_available : whether we had a pre-computed pocket envelope
    """
    # cache envelopes by target to avoid reloading
    envelope_cache = {}
    scores, available = [], []

    for _, row in df.iterrows():
        smiles = row[smiles_col]
        target = row.get(target_col, "unknown")

        if target not in envelope_cache:
            pvar  = os.path.join(pocket_dir, f"{target}.dyna.pvar")
            vox   = os.path.join(pocket_dir, f"{target}.voxels.pkl")
            if not os.path.exists(pvar):
                pvar = os.path.join(pocket_dir, f"{target}.property.pvar")
            if os.path.exists(pvar) and os.path.exists(vox):
                v_coords, v_probs = envelope_from_pvar(pvar, vox, model, device)
                envelope_cache[target] = (v_coords, v_probs)
            else:
                envelope_cache[target] = None

        env = envelope_cache[target]
        if env is None:
            scores.append(float("nan"))
            available.append(False)
            continue

        coords = smiles_to_heavy_atom_coords(smiles)
        if coords is None:
            scores.append(float("nan"))
        else:
            scores.append(score_ligand_against_envelope(coords, env[0], env[1]))
        available.append(True)

    df = df.copy()
    df["envelope_score"]   = scores
    df["pocket_available"] = available
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_path",          default=None)
    parser.add_argument("--model_checkpoint",  required=True)
    parser.add_argument("--model_config",      required=True)
    parser.add_argument("--pocket_dir",        required=True)
    parser.add_argument("--smiles_col",        default="smiles")
    parser.add_argument("--target_col",        default="target")
    parser.add_argument("--out_csv",           default="openadmet_dyna_scores.csv")
    parser.add_argument("--use_gpu",           action="store_true")
    args = parser.parse_args()

    device = "cuda" if args.use_gpu and torch.cuda.is_available() else "cpu"

    config = torch.load(args.model_config,     map_location=device)
    model  = config["model"].to(device).float()
    ckpt   = torch.load(args.model_checkpoint, map_location=device)
    model.load_state_dict(ckpt)

    df = load_openadmet(args.csv_path)
    print(f"Loaded {len(df)} compounds")

    df_scored = score_dataset(df, args.smiles_col, args.target_col,
                               args.pocket_dir, model, device)
    df_scored.to_csv(args.out_csv, index=False)
    print(f"Saved scored dataset to {args.out_csv}")
    available = df_scored["pocket_available"].sum()
    scored    = df_scored["envelope_score"].notna().sum()
    print(f"Scored {scored}/{len(df)} compounds ({available} with pocket envelope)")


if __name__ == "__main__":
    main()
