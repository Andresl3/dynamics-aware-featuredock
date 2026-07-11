#!/usr/bin/env python
"""
CDK2 pose-RMSD head-to-head: baseline (6x80) vs +Dyna-1 (6x81).

This computes the worksheet's PRIMARY metric -- ligand pose RMSD to the native
co-crystal pose, with the 2 A success threshold -- for both trained arms on the
held-out CDK2 test structures.

Pipeline per structure (self-docking / redocking):
  1. Rebuild each trained model from its checkpoint args (80 vs 81 auto).
  2. Forward the structure's FEATURE tensor -> per-grid-point binding probability.
  3. Pose the NATIVE ligand against that probability map using FeatureDock's own
     optimizer (virtual_screen.optimize_one_run_trimmed), nsamples restarts.
  4. Keep the best pose by the model's own alignment score (opt_score).
  5. RMSD(best predicted pose, native pose). Because this is redocking, the
     native ligand's crystal heavy-atom coords ARE the ground-truth pose in the
     SAME frame as the voxels, so RMSD is a direct Kabsch-free coordinate RMSD
     over matched heavy atoms (both come from the same molecule/atom order).

Outputs (under --outdir):
  cdk2_rmsd_per_structure.csv   per-pid best RMSD + success flag, both arms
  cdk2_rmsd_summary.csv/.json   mean/median RMSD, success rate (fraction <= 2 A)
  cdk2_rmsd_comparison.png      paired RMSD dumbbell + success-rate bars

NOTE on data requirements: needs, per pid, the pvar tensor (pvar_80 / pvar_81),
the {pid}.voxels.pkl, and the native ligand {pid}_ligand.sdf (or .mol). Point
--voxeldir and --ligdir at where those live on the cluster.
"""
import os, sys, json, argparse, pickle
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # src/
import torch
from models.evaluate_cdk2 import build_model_from_ckpt, predict_structure
# posing core from the repo's screening module
from application.virtual_screen import (optimize_one_run_trimmed, load_ligand_fromsdf,
                                        get_heavyatom)


def load_pvar(path):
    with open(path, 'rb') as f:
        return np.asarray(pickle.load(f))


def load_voxels(path):
    with open(path, 'rb') as f:
        return np.asarray(pickle.load(f))


def native_heavy_coords(ligfile):
    """Native ligand heavy-atom coordinates in the crystal frame + atom count."""
    mol = load_ligand_fromsdf(ligfile)
    if mol is None:
        # fall back to sanitize=False for awkward ligands
        import rdkit.Chem as Chem
        mol = Chem.MolFromMolFile(ligfile, sanitize=False)
    idx, coords = get_heavyatom(mol)
    return np.asarray(coords), len(idx)


def rmsd(a, b):
    """Heavy-atom RMSD, direct atom-indexed.

    Formula is verified algebraically identical (to 6 dp) to the ONE RMSD
    implementation found in the repo -- src/application/dbscan_cluster.py L48:
        pairwise_distances(X, metric=lambda x,y: np.sqrt(np.mean((x-y)**2)*3))
    on flattened (3M,) coords == sqrt(mean_atoms ‖pi-qi‖²). CAVEAT: that function
    (group_results_dbscan) is the pose-CLUSTERING distance used to DBSCAN candidate
    poses together (paper p.10). The paper's reported native-crystal RMSD accuracy
    metric (p.5: mean 2.4 A / median 2.1 A) is produced by a separate evaluation/
    postanalysis module NOT present in this repo checkout, so I could not confirm it
    uses this exact code path. What this function assumes -- and what a reader should
    check against the paper's eval code if/when available:
      * direct atom-indexed RMSD, NO Kabsch re-superposition (valid here because the
        pose is already in the native frame via the envelope alignment -- but the
        paper may superpose; if so, our RMSD is an UPPER BOUND on theirs);
      * NO symmetry/automorphism correction (symmetric ligands could read higher
        than a symmetry-aware RMSD would);
      * heavy atoms only ([!#1]); atom order preserved because the posed coords are a
        rigid transform of this same native heavy-atom array (atom i -> atom i).
    These are reasonable defaults, not confirmed matches to the paper's benchmark."""
    a, b = np.asarray(a), np.asarray(b)
    assert a.shape == b.shape, f"coord shape mismatch {a.shape} vs {b.shape}"
    return float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))


def _one_restart(args):
    """Module-level worker (picklable for multiprocessing): one seeded restart.
    Returns (opt_score, rmsd_to_native)."""
    native_heavy, prob_coords, prob_cutoff, seed_i = args
    np.random.seed(seed_i)   # per-restart seed -> reproducible + independent draws
    _, _, _, opt_score, aligned = optimize_one_run_trimmed(
        native_heavy, prob_coords, prob_cutoff=prob_cutoff, dist_cutoff=1.5)
    return opt_score, rmsd(aligned, native_heavy)


def pose_and_score(prob_coords, native_heavy, nsamples, prob_cutoff, seed,
                   nthreads=1, topk=4):
    """Run the optimizer nsamples times from the native conformer (each a random
    rotation, per the FeatureDock paper's "500 random rotations"). Select poses
    the way the paper does: sort by model score, take the top-k, and report the
    BEST RMSD among them ("the RMSD converged after picking 4 top-scored poses").
    Returns a dict:
      rmsd_top1   = RMSD of the single best-scoring pose (greedy; our old metric)
      rmsd_topk   = min RMSD among the top-k best-scoring poses (PAPER protocol)
      rmsd_oracle = min RMSD over ALL restarts (best the sampler ever found)
      score_top1  = the (highest) model score -- what selection maximises
      score_oracle= the model score OF the oracle (nearest-native) pose
      rank_oracle = 1-based rank of the oracle pose in the score-sorted list
                    (1 = the score DID pick the best pose; large = the correct
                    pose was buried far down the score ranking = scoring failure)
    The top1-vs-topk gap isolates a selection problem; topk-vs-oracle a sampling
    problem; rank_oracle quantifies the scoring failure directly. Restarts are
    independent -> parallel across `nthreads` processes."""
    tasks = [(native_heavy, prob_coords, prob_cutoff, seed + i) for i in range(nsamples)]
    if nthreads and nthreads > 1:
        import multiprocessing
        with multiprocessing.Pool(nthreads) as pool:
            results = pool.map(_one_restart, tasks)
    else:
        results = [_one_restart(t) for t in tasks]
    ranked = sorted(results, key=lambda t: t[0], reverse=True)  # by score, desc
    # oracle = the restart with the smallest RMSD; find its rank in the score order
    oracle_idx = min(range(len(results)), key=lambda i: results[i][1])
    oracle_score, rmsd_oracle = results[oracle_idx]
    rank_oracle = 1 + next(j for j, (s, _) in enumerate(ranked) if s == oracle_score
                           and _ == rmsd_oracle)
    return {"rmsd_top1": ranked[0][1],
            "rmsd_topk": min(r for _, r in ranked[:topk]),
            "rmsd_oracle": rmsd_oracle,
            "score_top1": ranked[0][0],
            "score_oracle": oracle_score,
            "rank_oracle": rank_oracle,
            "n_restarts": len(results)}


def run_arm(name, ckpt_path, datadir, voxeldir, ligdir, pids, device,
            nsamples, prob_cutoff, seed, nthreads=1, topk=4):
    ckpt = torch.load(ckpt_path, map_location=device)
    model, fps, nshell = build_model_from_ckpt(ckpt, device)
    print(f"[{name}] rebuilt model: feature_per_shell={fps}, num_shells={nshell}")
    rows = []
    for pid in pids:
        pv = os.path.join(datadir, f"{pid}.property.pvar")
        vx = os.path.join(voxeldir, f"{pid}.voxels.pkl")
        lig = None
        for ext in ("_ligand.sdf", "_ligand.mol", ".sdf", ".mol"):
            cand = os.path.join(ligdir, f"{pid}{ext}")
            if os.path.exists(cand):
                lig = cand; break
        if not (os.path.exists(pv) and os.path.exists(vx) and lig):
            print(f"  [skip] {pid}: missing pvar/voxels/ligand"); continue
        X = load_pvar(pv)
        coords = load_voxels(vx)
        _, p1 = predict_structure(model, X, device)          # prob of binding
        prob_coords = np.hstack([coords[:, :3], p1.reshape(-1, 1)])
        try:
            nat, natom = native_heavy_coords(lig)
        except Exception as e:
            print(f"  [skip] {pid}: ligand load failed ({e})"); continue
        res = pose_and_score(prob_coords, nat, nsamples, prob_cutoff,
                             seed, nthreads, topk)
        rows.append({"pid": pid, "n_heavy": natom,
                     "score_top1": round(res["score_top1"], 4),
                     "score_oracle": round(res["score_oracle"], 4),
                     "rank_oracle": res["rank_oracle"], "n_restarts": res["n_restarts"],
                     "rmsd_top1": round(res["rmsd_top1"], 3),
                     "rmsd_topk": round(res["rmsd_topk"], 3),
                     "rmsd_oracle": round(res["rmsd_oracle"], 3),
                     "success_2A": int(res["rmsd_topk"] <= 2.0)})   # paper metric
        print(f"  {pid}: top1={res['rmsd_top1']:.2f}  top{topk}={res['rmsd_topk']:.2f}  "
              f"oracle={res['rmsd_oracle']:.2f} A (rank {res['rank_oracle']}/{res['n_restarts']}, "
              f"score {res['score_oracle']:.3f} vs top1 {res['score_top1']:.3f})  "
              f"success(top{topk}<=2A)={res['rmsd_topk']<=2.0}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline-ckpt', required=True)
    ap.add_argument('--baseline-data', required=True, help='pvar_80 dir')
    ap.add_argument('--dyna1-ckpt', required=True)
    ap.add_argument('--dyna1-data', required=True, help='pvar_81 dir')
    ap.add_argument('--voxeldir', required=True, help='dir with {pid}.voxels.pkl')
    ap.add_argument('--ligdir', required=True, help='dir with native {pid}_ligand.sdf')
    ap.add_argument('--test-pids', required=True)
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--nsamples', type=int, default=50,
                    help='optimizer restarts per structure (best-by-score kept)')
    ap.add_argument('--prob-cutoff', type=float, default=0.5)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--use_gpu', action='store_true', default=False)
    ap.add_argument('--nthreads', type=int, default=1,
                    help='parallel processes for the pose restarts (CPU-bound; '
                         'set to your allocated core count for a speedup)')
    ap.add_argument('--topk', type=int, default=4,
                    help="report best RMSD among top-k scored poses (paper uses 4)")
    args = ap.parse_args()

    device = 'cuda' if (args.use_gpu and torch.cuda.is_available()) else 'cpu'
    os.makedirs(args.outdir, exist_ok=True)
    with open(args.test_pids) as f:
        pids = [l.strip() for l in f if l.strip()]
    print(f"Evaluating pose RMSD on {len(pids)} CDK2 structures (nsamples={args.nsamples})")

    base = run_arm("baseline80", args.baseline_ckpt, args.baseline_data,
                   args.voxeldir, args.ligdir, pids, device,
                   args.nsamples, args.prob_cutoff, args.seed, args.nthreads, args.topk)
    dyna = run_arm("dyna1_81", args.dyna1_ckpt, args.dyna1_data,
                   args.voxeldir, args.ligdir, pids, device,
                   args.nsamples, args.prob_cutoff, args.seed, args.nthreads, args.topk)

    # join per-pid (headline RMSD = paper's top-k selection)
    bd = {r['pid']: r for r in base}
    dd = {r['pid']: r for r in dyna}
    common = [p for p in pids if p in bd and p in dd]
    per = []
    for p in common:
        per.append({"pid": p,
                    "baseline_topk": bd[p]['rmsd_topk'], "baseline_top1": bd[p]['rmsd_top1'],
                    "baseline_oracle": bd[p]['rmsd_oracle'], "success_baseline": bd[p]['success_2A'],
                    "baseline_score_top1": bd[p]['score_top1'],
                    "baseline_score_oracle": bd[p]['score_oracle'], "baseline_rank_oracle": bd[p]['rank_oracle'],
                    "dyna1_topk": dd[p]['rmsd_topk'], "dyna1_top1": dd[p]['rmsd_top1'],
                    "dyna1_oracle": dd[p]['rmsd_oracle'], "success_dyna1": dd[p]['success_2A'],
                    "dyna1_score_top1": dd[p]['score_top1'],
                    "dyna1_score_oracle": dd[p]['score_oracle'], "dyna1_rank_oracle": dd[p]['rank_oracle'],
                    "delta_topk": round(dd[p]['rmsd_topk'] - bd[p]['rmsd_topk'], 3),
                    "delta_oracle": round(dd[p]['rmsd_oracle'] - bd[p]['rmsd_oracle'], 3)})

    import csv
    pcsv = os.path.join(args.outdir, "cdk2_rmsd_per_structure.csv")
    with open(pcsv, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(per[0].keys()) if per else ["pid"])
        w.writeheader(); w.writerows(per)

    def summ(rows, arm):
        rk = [r[f"{arm}_topk"] for r in rows]; r1 = [r[f"{arm}_top1"] for r in rows]
        ro = [r[f"{arm}_oracle"] for r in rows]; ss = [r[f"success_{arm}"] for r in rows]
        return {"mean_rmsd_topk": round(float(np.mean(rk)), 3),
                "median_rmsd_topk": round(float(np.median(rk)), 3),
                "mean_rmsd_top1": round(float(np.mean(r1)), 3),
                "mean_rmsd_oracle": round(float(np.mean(ro)), 3),
                "success_rate_2A": round(float(np.mean(ss)), 3),
                "n_success": int(np.sum(ss)), "n": len(rows)}

    summary = {"baseline": summ(per, "baseline"), "dyna1": summ(per, "dyna1"),
               "topk": args.topk, "nsamples": args.nsamples, "n_structures": len(per),
               "dyna1_better_count": int(sum(1 for r in per if r['delta_topk'] < 0))}
    with open(os.path.join(args.outdir, "cdk2_rmsd_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(args.outdir, "cdk2_rmsd_summary.csv"), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["arm", "mean_rmsd_topk", "median_rmsd_topk", "mean_rmsd_top1",
                    "mean_rmsd_oracle", "success_rate_2A", "n_success", "n"])
        for arm in ("baseline", "dyna1"):
            s = summary[arm]; w.writerow([arm, s["mean_rmsd_topk"], s["median_rmsd_topk"],
                s["mean_rmsd_top1"], s["mean_rmsd_oracle"], s["success_rate_2A"],
                s["n_success"], s["n"]])

    print(f"\n=== CDK2 pose-RMSD head-to-head (paper protocol: top-{args.topk} of "
          f"{args.nsamples} rotations) ===")
    for arm in ("baseline", "dyna1"):
        s = summary[arm]
        print(f"  {arm:9s}: top{args.topk} mean={s['mean_rmsd_topk']:.2f} median={s['median_rmsd_topk']:.2f} "
              f"| top1 mean={s['mean_rmsd_top1']:.2f} | oracle mean={s['mean_rmsd_oracle']:.2f} A "
              f"| success(top{args.topk}<=2A)={s['success_rate_2A']:.2f} ({s['n_success']}/{s['n']})")
    print(f"  dyna1 lower top{args.topk}-RMSD in {summary['dyna1_better_count']}/{len(per)} structures")

    _plot(per, summary, os.path.join(args.outdir, "cdk2_rmsd_comparison.png"))
    print(f"\nWrote: {pcsv}, cdk2_rmsd_summary.csv/.json, cdk2_rmsd_comparison.png")


def _plot(per, summary, outpath):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    per = sorted(per, key=lambda r: r['baseline_topk'])
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.8))
    y = np.arange(len(per))
    rb = [r['baseline_topk'] for r in per]; rd = [r['dyna1_topk'] for r in per]
    for i in range(len(per)):
        ax[0].plot([rb[i], rd[i]], [i, i], color='#cccccc', zorder=1)
    ax[0].scatter(rb, y, color='#8c8c8c', label='baseline (6x80)', zorder=2, s=22)
    ax[0].scatter(rd, y, color='#2c7fb8', label='+Dyna-1 (6x81)', zorder=2, s=22)
    ax[0].axvline(2.0, color='#c0504d', ls='--', lw=1, label='2 A success')
    ax[0].set_yticks(y); ax[0].set_yticklabels([r['pid'] for r in per], fontsize=6)
    ax[0].set_xlabel('pose RMSD to native (A)')
    ax[0].set_title('Per-structure pose RMSD', loc='left')
    ax[0].legend(frameon=False, fontsize=7)
    arms = ['baseline', 'dyna1']
    sr = [summary[a]['success_rate_2A'] for a in arms]
    mr = [summary[a]['mean_rmsd_topk'] for a in arms]
    xb = np.arange(2)
    b = ax[1].bar(xb, sr, 0.5, color=['#8c8c8c', '#2c7fb8'])
    ax[1].set_xticks(xb); ax[1].set_xticklabels(['baseline', '+Dyna-1'])
    ax[1].set_ylabel('success rate (RMSD <= 2 A)'); ax[1].set_ylim(0, 1)
    ax[1].set_title('Docking success rate', loc='left')
    for xi, (s, m) in enumerate(zip(sr, mr)):
        ax[1].text(xi, s + 0.02, f'{s:.2f}\n(mean {m:.1f} A)', ha='center', va='bottom', fontsize=7)
    fig.suptitle(f'CDK2 self-docking: pose RMSD, baseline vs +Dyna-1 ({summary["n_structures"]} structures)',
                 fontsize=9, y=1.02)
    fig.tight_layout()
    fig.savefig(outpath, dpi=200, bbox_inches='tight')


if __name__ == '__main__':
    main()
