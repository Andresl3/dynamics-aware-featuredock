"""
train_dynamics_aware.py
=======================
Train FeatureDock (baseline OR +Dyna-1 dynamics channel) on ALL of PDBBind
v2020, holding out CDK2 as the validation set.

Difference from the stock src/models/train_main.py:
  * train_main.py builds a RANDOM clan-fold split each run.
  * this script reads EXPLICIT --train-pids / --val-pids lists (produced by
    make_cdk2_split.py) so the split is fixed: everything except CDK2 trains,
    CDK2 validates.
  * honours --feature_per_shell (80 baseline / 81 +Dyna-1) via parse_config.

It reuses FeatureDock's own ClassifierDataset, model builders, loss and
optimizer, so training dynamics are identical to the paper -- only the split
and the input width change.

Example (run BOTH arms to compare):
  python train_dynamics_aware.py --modeltype transformer --feature_per_shell 80 \
      --datafolder $DATA/pvar_80 --train-pids train_pids.txt --val-pids val_pids.txt \
      --outfolder results/baseline  --steps 300 --use_gpu --modelname baseline80
  python train_dynamics_aware.py --modeltype transformer --feature_per_shell 81 \
      --datafolder $DATA/pvar_81 --train-pids train_pids.txt --val-pids val_pids.txt \
      --outfolder results/dyna1     --steps 300 --use_gpu --modelname dyna1_81
"""
import os
import sys
import json
import glob
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from sklearn.metrics import precision_recall_fscore_support as score
from sklearn.metrics import accuracy_score, matthews_corrcoef

filename = os.path.abspath(__file__)
parentdir = os.path.dirname(os.path.dirname(filename))  # src
sys.path.append(parentdir)
from models.loaders import ClassifierDataset
from models.earlystop import EarlyStopping
from models.train_utils import init_seed, count_parameters


# ------------------------------------------------------------------ config
def build_parser():
    p = argparse.ArgumentParser(description="Train FeatureDock with CDK2-as-validation split.")
    p.add_argument('--modeltype', default='transformer', choices=['cnn', 'fnn', 'transformer'])
    p.add_argument('--feature_per_shell', type=int, default=80,
                   help='80 baseline / 81 +Dyna-1 dynamics channel')
    p.add_argument('--num_shells', type=int, default=6)
    p.add_argument('--task', default='HeavyAtomsite', help='label suffix')
    p.add_argument('--datafolder', required=True, help='folder of <pid>.property.pvar + labels')
    p.add_argument('--train-pids', required=True, help='newline PID list for training')
    p.add_argument('--val-pids', required=True, help='newline PID list for validation (CDK2)')
    p.add_argument('--outfolder', required=True)
    p.add_argument('--modelname', default=None)
    p.add_argument('--n_blocks', type=int, default=5)
    p.add_argument('--hidden_size', type=int, default=64)
    p.add_argument('--intermediate_size', type=int, default=64)
    p.add_argument('--num_attention_heads', type=int, default=2)
    p.add_argument('--lr', type=float, default=1e-3)
    p.add_argument('--weight_decay', type=float, default=0.0)
    p.add_argument('--steps', type=int, default=300)
    p.add_argument('--n_structs', type=int, default=8, help='structures per batch')
    p.add_argument('--n_resamples', type=int, default=1000, help='resampled points per structure')
    p.add_argument('--save_every', type=int, default=25)
    p.add_argument('--patience', type=int, default=30)
    p.add_argument('--earlystop', action='store_true')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--use_gpu', action='store_true')
    p.add_argument('--warm-start', default=None,
                   help='pretrained checkpoint to warm-start from (e.g. one of the '
                        'repo\'s results/vit_20/HeavyAtomsite_transformer_20_seed*.torch). '
                        'Layers whose shape matches are loaded; shape-mismatched layers '
                        '(e.g. norm_layer 80->81 for the Dyna-1 channel) are reinitialized.')
    return p


def build_model(args, device):
    n_class = 2
    fps, nshell = args.feature_per_shell, args.num_shells
    in_dim = fps * nshell
    print(f"Model input width: {nshell} shells x {fps} props = {in_dim}")
    if args.modeltype == 'transformer':
        from models.transformer_models import BertSentClassifier
        model = BertSentClassifier(n_class=n_class, num_shells=nshell, feature_per_shell=fps,
                                   hidden_size=args.hidden_size, intermediate_size=args.intermediate_size,
                                   num_hidden_layers=args.n_blocks, num_attention_heads=args.num_attention_heads,
                                   max_position_embeddings=100, layer_norm_eps=1e-12,
                                   hidden_dropout_prob=0.1, attention_probs_dropout_prob=0.1, option='finetune')
    elif args.modeltype == 'cnn':
        from models.customise_models import FeatIntResNet
        model = FeatIntResNet(feature_per_shell=fps, num_shells=nshell, n_blocks=args.n_blocks,
                              n_mix=2, n_class=n_class, activation='relu', noise=None)
    else:  # fnn
        from models.customise_models import get_fnn_model
        model = get_fnn_model(in_dim, [], n_class, dropout=0.5)
    return model.float().to(device)


def warm_start(model, ckpt_path, device):
    """Load a pretrained checkpoint into `model`, keeping only shape-matching
    tensors; shape-mismatched layers keep their fresh init.

    Going 6x80 -> 6x81 changes exactly the input-facing layer that carries a
    per-property dimension: in the transformer that is
    `norm_layer = nn.BatchNorm2d(feature_per_shell)` (80 -> 81), NOT `word2dense`
    (which projects the num_shells axis and is unchanged). We therefore load
    everything that fits and reinitialize only the mismatched tensor(s), so a
    warm-start from the baseline-80 checkpoints is valid for the 81-channel model.
    """
    raw = torch.load(ckpt_path, map_location=device)
    src = raw.get('model_state_dict', raw)  # accept raw state_dict or wrapped ckpt
    tgt = model.state_dict()
    loaded, skipped = [], []
    for k, v in src.items():
        if k in tgt and tgt[k].shape == v.shape:
            tgt[k] = v
            loaded.append(k)
        else:
            skipped.append(k)
    model.load_state_dict(tgt)
    print(f"[warm-start] from {os.path.basename(ckpt_path)}: "
          f"loaded {len(loaded)} tensors, reinitialized {len(skipped)}")
    if skipped:
        print(f"[warm-start] reinitialized (shape change / not in checkpoint): {skipped}")
    return model


def load_pids(path, pool):
    ids = [x.strip().lower() for x in open(path) if x.strip()]
    have = [p for p in ids if p in pool]
    missing = sorted(set(ids) - set(pool))
    if missing:
        print(f"  [warn] {len(missing)} PID(s) in {os.path.basename(path)} not featurized "
              f"(skipped): e.g. {missing[:5]}")
    return have


# ------------------------------------------------------------------ epochs
def run_epoch(model, loader, loss_fn, optimizer, device, train):
    model.train() if train else model.eval()
    losses, preds, truth = [], [], []
    ctx = torch.enable_grad() if train else torch.no_grad()
    with ctx:
        for x, y in loader:
            s = x.shape
            x = x.reshape((s[0] * s[1], *s[2:])).float().to(device)
            y = y.reshape(-1).long().to(device)
            out = model(x)
            loss = loss_fn(out, y)
            if train:
                optimizer.zero_grad(); loss.backward(); optimizer.step()
            losses.append(float(loss))
            yp = torch.argmax(torch.softmax(out, 1), 1)
            preds.extend(yp.cpu().numpy().tolist()); truth.extend(y.cpu().numpy().tolist())
    acc = accuracy_score(truth, preds)
    mcc = matthews_corrcoef(truth, preds) if len(set(truth)) > 1 else 0.0
    pr = score(truth, preds, average='binary', zero_division=0)
    return np.mean(losses), acc, mcc, pr[0], pr[1], pr[2]


def main():
    args = build_parser().parse_args()
    init_seed(args.seed)
    device = 'cuda' if (args.use_gpu and torch.cuda.is_available()) else 'cpu'
    print(f"Device: {device}")
    os.makedirs(args.outfolder, exist_ok=True)
    modelname = args.modelname or f"{args.modeltype}_fps{args.feature_per_shell}"

    pool = {os.path.basename(f).split('.')[0].lower()
            for f in glob.glob(os.path.join(args.datafolder, '*.property.pvar'))}
    print(f"Featurized pool: {len(pool)} structures")
    train_pids = load_pids(args.train_pids, pool)
    val_pids = load_pids(args.val_pids, pool)
    print(f"Train: {len(train_pids)}  Val (CDK2): {len(val_pids)}")
    assert train_pids, "no training structures found in datafolder"
    assert val_pids, "no CDK2 validation structures found -- did you featurize them?"

    model = build_model(args, device)
    if args.warm_start:
        model = warm_start(model, args.warm_start, device)
    print("Tunable params:", count_parameters(model))
    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    train_ds = ClassifierDataset(args.datafolder, train_pids, suffix=args.task,
                                 resample=True, n_resamples=args.n_resamples)
    val_ds = ClassifierDataset(args.datafolder, val_pids, suffix=args.task,
                               resample=True, n_resamples=args.n_resamples)
    train_ld = DataLoader(train_ds, batch_size=args.n_structs, shuffle=True)
    val_ld = DataLoader(val_ds, batch_size=args.n_structs, shuffle=False)

    stopper = EarlyStopping(patience=args.patience, verbose=False) if args.earlystop else None
    history = []
    for step in range(1, args.steps + 1):
        tr = run_epoch(model, train_ld, loss_fn, optimizer, device, train=True)
        va = run_epoch(model, val_ld, loss_fn, optimizer, device, train=False)
        row = {'step': step,
               'train_loss': tr[0], 'train_acc': tr[1], 'train_mcc': tr[2],
               'val_loss': va[0], 'val_acc': va[1], 'val_mcc': va[2],
               'val_precision': va[3], 'val_recall': va[4], 'val_f1': va[5]}
        history.append(row)
        if step % 5 == 0 or step == 1:
            print(f"[{step:4d}] train_loss={tr[0]:.4f} acc={tr[1]:.3f} | "
                  f"val_loss={va[0]:.4f} acc={va[1]:.3f} mcc={va[2]:.3f} f1={va[5]:.3f}")
        if step % args.save_every == 0:
            torch.save({'model_state_dict': model.state_dict(),
                        'optimizer_state_dict': optimizer.state_dict(),
                        'step': step, 'args': vars(args)},
                       os.path.join(args.outfolder, f"{modelname}_step{step}.torch"))
        if stopper is not None:
            stopper(va[0], model)
            if stopper.early_stop:
                print(f"Early stop at step {step}"); break

    torch.save({'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'args': vars(args)},
               os.path.join(args.outfolder, f"{modelname}_final_params.torch"))
    with open(os.path.join(args.outfolder, f"{modelname}_history.json"), 'w') as f:
        json.dump(history, f, indent=2)
    print(f"Saved final params + history to {args.outfolder}")


if __name__ == "__main__":
    main()
