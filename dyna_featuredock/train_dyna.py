"""
Train DynaFeatureDock — FeatureDock + Dyna-1 dynamics token.

Usage
-----
python dyna_featuredock/train_dyna.py \
    --dyna_dir    /data/augmented_pvars \
    --orig_dir    /data/voxels \
    --pdbids_file data/labeled_pdblist.txt \
    --split_pkl   data/train_val_test_split.pkl \
    --out_dir     results/dyna_model \
    [--no_dynamics]        # ablation: train without the dynamics token
    [--hidden_size 20]
    [--n_layers 5]
    [--epochs 50]
    [--lr 1e-4]
    [--seed 42]
"""

import os
import sys
import pickle
import argparse
import random
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import Adam
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from models.earlystop import EarlyStopping   # type: ignore

from dyna_loaders import DynaClassifierDataset
from dyna_transformer import DynaBertSentClassifier


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def collate_fn(batch):
    """Stack variable-length batches from ClassifierDataset."""
    xs, ys = zip(*batch)
    return torch.cat(xs), torch.cat(ys)


def run_epoch(model, loader, criterion, optimizer, device, train=True):
    model.train(train)
    total_loss, total_n = 0.0, 0
    with torch.set_grad_enabled(train):
        for x, y in loader:
            x, y = x.to(device), y.to(device).long()
            logits = model(x)
            loss = criterion(logits, y)
            if train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * len(y)
            total_n += len(y)
    return total_loss / total_n


def accuracy(model, loader, device):
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device).long()
            preds = model(x).argmax(dim=1)
            correct += (preds == y).sum().item()
            total += len(y)
    return correct / total if total > 0 else 0.0


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dyna_dir",    required=True)
    parser.add_argument("--orig_dir",    required=True)
    parser.add_argument("--pdbids_file", required=True)
    parser.add_argument("--split_pkl",   required=True)
    parser.add_argument("--out_dir",     required=True)
    parser.add_argument("--no_dynamics", action="store_true",
                        help="Ablation: train without dynamics token")
    parser.add_argument("--hidden_size",    type=int, default=20)
    parser.add_argument("--intermediate",   type=int, default=80)
    parser.add_argument("--n_layers",       type=int, default=5)
    parser.add_argument("--n_heads",        type=int, default=4)
    parser.add_argument("--epochs",         type=int, default=50)
    parser.add_argument("--lr",             type=float, default=1e-4)
    parser.add_argument("--batch_size",     type=int, default=32)
    parser.add_argument("--n_resamples",    type=int, default=2000)
    parser.add_argument("--seed",           type=int, default=42)
    parser.add_argument("--patience",       type=int, default=10)
    parser.add_argument("--use_gpu",        action="store_true")
    args = parser.parse_args()

    set_seed(args.seed)
    device = "cuda" if args.use_gpu and torch.cuda.is_available() else "cpu"
    use_dynamics = not args.no_dynamics
    os.makedirs(args.out_dir, exist_ok=True)

    # load splits
    with open(args.split_pkl, "rb") as f:
        splits = pickle.load(f)
    train_ids = splits["train"]
    val_ids   = splits["val"]
    test_ids  = splits.get("test", [])

    ds_kwargs = dict(datadir=args.dyna_dir, orig_datadir=args.orig_dir,
                     resample=True, n_resamples=args.n_resamples,
                     use_dynamics=use_dynamics)
    train_ds = DynaClassifierDataset(pids=train_ids, **ds_kwargs)
    val_ds   = DynaClassifierDataset(pids=val_ids,   resample=False,
                                     datadir=args.dyna_dir,
                                     orig_datadir=args.orig_dir,
                                     use_dynamics=use_dynamics)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size,
                              shuffle=True,  collate_fn=collate_fn, num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size,
                              shuffle=False, collate_fn=collate_fn, num_workers=0)

    model = DynaBertSentClassifier(
        n_class=2,
        num_shells=6,
        feature_per_shell=80,
        hidden_size=args.hidden_size,
        intermediate_size=args.intermediate,
        num_hidden_layers=args.n_layers,
        num_attention_heads=args.n_heads,
        max_position_embeddings=100,
        hidden_dropout_prob=0.5,
        attention_probs_dropout_prob=0.1,
        use_dynamics=use_dynamics,
    ).to(device)

    optimizer = Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()
    stopper   = EarlyStopping(patience=args.patience, verbose=True,
                              path=os.path.join(args.out_dir, "best_checkpoint.pt"))

    print(f"[train] device={device}  use_dynamics={use_dynamics}  "
          f"train={len(train_ids)}  val={len(val_ids)}")

    for epoch in range(1, args.epochs + 1):
        train_loss = run_epoch(model, train_loader, criterion, optimizer, device)
        val_loss   = run_epoch(model, val_loader,   criterion, optimizer, device,
                               train=False)
        val_acc    = accuracy(model, val_loader, device)
        print(f"Epoch {epoch:3d}  train_loss={train_loss:.4f}  "
              f"val_loss={val_loss:.4f}  val_acc={val_acc:.4f}")
        stopper(val_loss, model)
        if stopper.early_stop:
            print("Early stopping triggered.")
            break

    # save config
    config_path = os.path.join(args.out_dir, "config.torch")
    torch.save({"model": model, "args": vars(args)}, config_path)
    print(f"Training complete. Best model: {stopper.path}")


if __name__ == "__main__":
    main()
