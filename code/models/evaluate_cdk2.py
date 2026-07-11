#!/usr/bin/env python
"""
Evaluate baseline (6x80) vs +Dyna-1 (6x81) FeatureDock models on the held-out
CDK2 test set -- the head-to-head that answers the project question: does the
Dyna-1 motion channel improve binding-site prediction on the flexible CDK2 pocket?

Both models are rebuilt from their own checkpoints' saved `args` (so 80 vs 81 is
automatic), then scored on EVERY grid point of each CDK2 structure (resample=False,
deterministic -- not a resampled subset). Metrics per structure: accuracy, MCC, F1,
precision, recall, ROC-AUC. Writes a per-structure CSV, a summary CSV, and a
head-to-head comparison figure.

Usage:
  python evaluate_cdk2.py \
      --baseline-ckpt RES/baseline80/baseline80_final_params.torch --baseline-data OUT80 \
      --dyna1-ckpt    RES/dyna1_81/dyna1_81_final_params.torch     --dyna1-data    OUT81 \
      --test-pids     OUT_DIR/test_pids.txt \
      --outdir        RES/cdk2_eval --use_gpu
"""
import os, sys, argparse, json
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (accuracy_score, matthews_corrcoef, roc_auc_score,
                             precision_recall_fscore_support as score)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # src/
from models.loaders import ClassifierDataset


def build_model_from_ckpt(ckpt, device):
    """Rebuild the exact model architecture recorded in the checkpoint's args."""
    a = ckpt['args']
    fps, nshell = a['feature_per_shell'], a['num_shells']
    from models.transformer_models import BertSentClassifier
    model = BertSentClassifier(
        n_class=2, num_shells=nshell, feature_per_shell=fps,
        hidden_size=a['hidden_size'], intermediate_size=a['intermediate_size'],
        num_hidden_layers=a['n_blocks'], num_attention_heads=a['num_attention_heads'],
        max_position_embeddings=100, layer_norm_eps=1e-12,
        hidden_dropout_prob=0.1, attention_probs_dropout_prob=0.1, option='finetune')
    model.load_state_dict(ckpt['model_state_dict'])
    return model.float().to(device).eval(), fps, nshell


@torch.no_grad()
def predict_structure(model, X, device):
    """Return (pred_label, prob_of_class1) for every grid point of one structure."""
    x = torch.from_numpy(X).float().to(device)
    out = model(x)
    probs = torch.softmax(out, 1)
    pred = torch.argmax(probs, 1).cpu().numpy()
    p1 = probs[:, 1].cpu().numpy()
    return pred, p1


def metrics(truth, pred, prob1):
    truth = np.asarray(truth).astype(int)
    acc = accuracy_score(truth, pred)
    mcc = matthews_corrcoef(truth, pred) if len(set(truth)) > 1 else float('nan')
    pr = score(truth, pred, average='binary', zero_division=0)
    try:
        auc = roc_auc_score(truth, prob1) if len(set(truth)) > 1 else float('nan')
    except ValueError:
        auc = float('nan')
    return dict(acc=acc, mcc=mcc, precision=pr[0], recall=pr[1], f1=pr[2], auc=auc,
                n_points=len(truth), n_pos=int(truth.sum()))


def eval_arm(ckpt_path, datafolder, pids, task, device):
    ckpt = torch.load(ckpt_path, map_location=device)
    model, fps, nshell = build_model_from_ckpt(ckpt, device)
    ds = ClassifierDataset(datafolder, pids, suffix=task, resample=False)
    rows = {}
    for i, pid in enumerate(pids):
        try:
            X, Y = ds[i]
            X = X.numpy(); Y = Y.numpy()
            pred, p1 = predict_structure(model, X, device)
            rows[pid] = metrics(Y, pred, p1)
        except Exception as e:
            print(f"  [warn] {pid}: {type(e).__name__}: {str(e)[:100]}")
            rows[pid] = None
    return rows, fps


def main():
    ap = argparse.ArgumentParser(description="CDK2 head-to-head: baseline80 vs dyna1_81.")
    ap.add_argument('--baseline-ckpt', required=True)
    ap.add_argument('--baseline-data', required=True, help='pvar_80 folder')
    ap.add_argument('--dyna1-ckpt', required=True)
    ap.add_argument('--dyna1-data', required=True, help='pvar_81 folder')
    ap.add_argument('--test-pids', required=True)
    ap.add_argument('--task', default='HeavyAtomsite')
    ap.add_argument('--outdir', default='cdk2_eval')
    ap.add_argument('--use_gpu', action='store_true')
    args = ap.parse_args()

    device = torch.device('cuda' if (args.use_gpu and torch.cuda.is_available()) else 'cpu')
    os.makedirs(args.outdir, exist_ok=True)
    pids = [l.strip() for l in open(args.test_pids) if l.strip()]
    print(f"Evaluating {len(pids)} CDK2 test structures on device={device}")

    print("[baseline 6x80]"); base_rows, base_fps = eval_arm(
        args.baseline_ckpt, args.baseline_data, pids, args.task, device)
    print("[+Dyna-1 6x81]"); dyna_rows, dyna_fps = eval_arm(
        args.dyna1_ckpt, args.dyna1_data, pids, args.task, device)
    assert base_fps == 80 and dyna_fps == 81, \
        f"unexpected feature widths: baseline={base_fps}, dyna1={dyna_fps}"

    # per-structure table
    recs = []
    for pid in pids:
        b, d = base_rows.get(pid), dyna_rows.get(pid)
        if b is None or d is None:
            continue
        rec = {'pid': pid}
        for k in ('acc', 'mcc', 'f1', 'auc', 'precision', 'recall'):
            rec[f'baseline_{k}'] = b[k]; rec[f'dyna1_{k}'] = d[k]
            rec[f'delta_{k}'] = d[k] - b[k]
        rec['n_points'] = b['n_points']; rec['n_pos'] = b['n_pos']
        recs.append(rec)
    df = pd.DataFrame(recs)
    per_csv = os.path.join(args.outdir, 'cdk2_per_structure.csv')
    df.to_csv(per_csv, index=False)

    # summary (mean over structures, plus a pooled-points note)
    summ = {}
    for k in ('acc', 'mcc', 'f1', 'auc', 'precision', 'recall'):
        summ[k] = {'baseline_mean': float(df[f'baseline_{k}'].mean()),
                   'dyna1_mean': float(df[f'dyna1_{k}'].mean()),
                   'delta_mean': float(df[f'delta_{k}'].mean()),
                   'dyna1_better_n': int((df[f'delta_{k}'] > 0).sum()),
                   'n_structures': int(df[f'delta_{k}'].notna().sum())}
    summ_csv = os.path.join(args.outdir, 'cdk2_summary.csv')
    pd.DataFrame(summ).T.to_csv(summ_csv)
    with open(os.path.join(args.outdir, 'cdk2_summary.json'), 'w') as f:
        json.dump(summ, f, indent=2)

    print("\n=== CDK2 head-to-head (mean over structures) ===")
    for k, v in summ.items():
        print(f"  {k:9s}: baseline={v['baseline_mean']:.3f}  dyna1={v['dyna1_mean']:.3f}  "
              f"delta={v['delta_mean']:+.3f}  (dyna1 better in {v['dyna1_better_n']}/{v['n_structures']})")

    # figure
    try:
        make_figure(df, summ, args.outdir)
    except Exception as e:
        print(f"[warn] figure failed: {type(e).__name__}: {e}")
    print(f"\nWrote:\n  {per_csv}\n  {summ_csv}\n  {os.path.join(args.outdir,'cdk2_comparison.png')}")


def make_figure(df, summ, outdir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    metrics_to_plot = ['mcc', 'f1', 'auc', 'acc']
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))

    # (a) grouped bar of means
    ax = axes[0]
    x = np.arange(len(metrics_to_plot)); w = 0.38
    base = [summ[m]['baseline_mean'] for m in metrics_to_plot]
    dyna = [summ[m]['dyna1_mean'] for m in metrics_to_plot]
    ax.bar(x - w/2, base, w, label='baseline (6x80)', color='#8c8c8c')
    ax.bar(x + w/2, dyna, w, label='+Dyna-1 (6x81)', color='#2c7fb8')
    ax.set_xticks(x); ax.set_xticklabels([m.upper() for m in metrics_to_plot])
    ax.set_ylabel('mean over 18 CDK2 structures'); ax.set_ylim(0, 1)
    ax.set_title('(a) CDK2 test-set metrics'); ax.legend(frameon=False)
    for i, (b, d) in enumerate(zip(base, dyna)):
        ax.text(i - w/2, b + 0.01, f'{b:.2f}', ha='center', va='bottom', fontsize=8)
        ax.text(i + w/2, d + 0.01, f'{d:.2f}', ha='center', va='bottom', fontsize=8)

    # (b) per-structure paired MCC (shows who wins where)
    ax = axes[1]
    d2 = df.dropna(subset=['baseline_mcc', 'dyna1_mcc']).sort_values('baseline_mcc')
    yy = np.arange(len(d2))
    ax.hlines(yy, d2['baseline_mcc'], d2['dyna1_mcc'], color='#cccccc', zorder=1)
    ax.scatter(d2['baseline_mcc'], yy, s=28, color='#8c8c8c', label='baseline', zorder=2)
    ax.scatter(d2['dyna1_mcc'], yy, s=28, color='#2c7fb8', label='+Dyna-1', zorder=2)
    ax.set_yticks(yy); ax.set_yticklabels(d2['pid'], fontsize=7)
    ax.set_xlabel('MCC'); ax.set_title('(b) per-structure MCC (baseline \u2192 +Dyna-1)')
    ax.legend(frameon=False, loc='lower right')
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'cdk2_comparison.png'), dpi=200, bbox_inches='tight')


if __name__ == '__main__':
    main()
