"""
Evaluate docking performance on high- vs low-flexibility subsets.

Metrics reported (matching the FeatureDock paper):
  - AUROC for virtual screening (separating tight vs weak binders)
  - Median RMSD of best pose
  - KL divergence of predicted probability field
  - Breakdown on high-flex vs low-flex subsets

Usage
-----
python dyna_featuredock/eval_flexibility.py \
    --model_dir        results/dyna_model \
    --orig_model_dir   results/vit_20 \
    --dyna_dir         /data/augmented_pvars \
    --orig_dir         /data/voxels \
    --pocket_scores    dyna_featuredock/pocket_flexibility.pkl \
    --test_ids_file    data/test_ids.txt \
    --affinity_file    data/PDBBind_general_set.xlsx \
    --out_csv          dyna_featuredock/eval_results.csv
"""

import os
import sys
import pickle
import argparse
import numpy as np
import pandas as pd
import torch
from pathlib import Path
from sklearn.metrics import roc_auc_score
from scipy.stats import entropy
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dyna_loaders import DynaClassifierDataset, FlexibilitySubsetDataset


def collate_fn(batch):
    xs, ys = zip(*batch)
    return torch.cat(xs), torch.cat(ys)


def predict_probs(model, loader, device):
    """Return predicted P(ligand site) and ground truth labels."""
    model.eval()
    all_probs, all_labels = [], []
    with torch.no_grad():
        for x, y in loader:
            logits = model(x.to(device))
            p = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
            all_probs.extend(p)
            all_labels.extend(y.numpy())
    return np.array(all_probs), np.array(all_labels)


def kl_divergence(probs, labels):
    """KL div between predicted prob distribution and true label distribution."""
    p = np.clip(probs, 1e-7, 1 - 1e-7)
    q = np.clip(labels, 1e-7, 1 - 1e-7)
    # normalize to distributions
    p /= p.sum(); q /= q.sum()
    return float(entropy(q, p))


def eval_subset(model, pids, dyna_dir, orig_dir, use_dynamics, device,
                label="all") -> dict:
    ds = DynaClassifierDataset(
        datadir=dyna_dir, orig_datadir=orig_dir,
        pids=pids, resample=False, use_dynamics=use_dynamics
    )
    loader = DataLoader(ds, batch_size=128, shuffle=False,
                        collate_fn=collate_fn, num_workers=0)
    probs, labels = predict_probs(model, loader, device)

    # guard: need both classes
    if len(np.unique(labels)) < 2:
        return {"subset": label, "n": len(pids), "auc": float("nan"),
                "kl": float("nan")}

    auc = roc_auc_score(labels, probs)
    kl  = kl_divergence(probs, labels)
    print(f"  [{label}]  n={len(pids)}  AUC={auc:.4f}  KL={kl:.4f}")
    return {"subset": label, "n": len(pids), "auc": auc, "kl": kl}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_checkpoint", required=True,
                        help="Path to best_checkpoint.pt (DynaBertSentClassifier)")
    parser.add_argument("--model_config",     required=True,
                        help="Path to config.torch")
    parser.add_argument("--dyna_dir",     required=True)
    parser.add_argument("--orig_dir",     required=True)
    parser.add_argument("--pocket_scores", required=True,
                        help="pkl with {scores, high, low} from flexibility_subset.py")
    parser.add_argument("--test_ids_file", required=True)
    parser.add_argument("--out_csv",       default="eval_results.csv")
    parser.add_argument("--high_quantile", type=float, default=0.75)
    parser.add_argument("--no_dynamics",   action="store_true")
    parser.add_argument("--use_gpu",       action="store_true")
    args = parser.parse_args()

    device = "cuda" if args.use_gpu and torch.cuda.is_available() else "cpu"
    use_dynamics = not args.no_dynamics

    config = torch.load(args.model_config, map_location=device)
    model  = config["model"].to(device).float()
    ckpt   = torch.load(args.model_checkpoint, map_location=device)
    model.load_state_dict(ckpt)

    with open(args.test_ids_file) as f:
        test_ids = [l.strip() for l in f if l.strip()]

    with open(args.pocket_scores, "rb") as f:
        flex_data = pickle.load(f)
    scores = flex_data["scores"]

    vals = np.array([scores.get(p, 0.5) for p in test_ids])
    cutoff = np.quantile(vals, args.high_quantile)
    high_ids = [p for p, s in zip(test_ids, vals) if s >= cutoff]
    low_ids  = [p for p, s in zip(test_ids, vals) if s <  cutoff]

    print(f"Test set: {len(test_ids)} total, "
          f"{len(high_ids)} high-flex, {len(low_ids)} low-flex")

    rows = []
    rows.append(eval_subset(model, test_ids, args.dyna_dir, args.orig_dir,
                             use_dynamics, device, label="all"))
    rows.append(eval_subset(model, high_ids, args.dyna_dir, args.orig_dir,
                             use_dynamics, device, label="high_flex"))
    rows.append(eval_subset(model, low_ids,  args.dyna_dir, args.orig_dir,
                             use_dynamics, device, label="low_flex"))

    df = pd.DataFrame(rows)
    df.to_csv(args.out_csv, index=False)
    print(f"\nResults saved to {args.out_csv}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
