"""
make_cdk2_split.py
==================
Build a CDK2-as-validation train/val split for Dynamics-aware FeatureDock.

Goal: train on ALL of PDBBind v2020 (refined set) and hold out CDK2 as the
validation set, so validation measures generalization to the worksheet's
headline flexible target.

The pool of trainable structures = every `<pid>.property.pvar` file present in
--datafolder (whatever you featurized on Colab). The CDK2 validation set is
removed from the training pool. Two definitions of "CDK2" are supported:

  --cdk2-scope crystals  : only the CDK2 crystal structures that are in PDBBind
                           (data/cdk2_in_PDBBind.txt, 18 ids). Minimal hold-out.

  --cdk2-scope homologs  : the CDK2 90%-sequence-identity set
                           (data/cdk2_1h00_90identity.txt, 438 ids) intersected
                           with the pool. RECOMMENDED -- prevents close CDK2
                           relatives from leaking into training, which would
                           inflate validation performance.

  --cdk2-scope clan      : leakage-safe by cluster. Take every clan in
                           ClanGraph_90_df.pkl that contains ANY CDK2 crystal or
                           homolog, and hold out the ENTIRE clan(s). Strongest
                           guarantee of no train/val homology leakage.

Outputs two newline-delimited lists consumed by the training script:
    train_pids.txt   val_pids.txt

These are drop-in for a train_main.py variant that reads explicit PID lists
(see step3b_train_dynamics_aware.sh) instead of the random clan-fold split.
"""
import os
import glob
import pickle
import argparse


def load_lines(path):
    with open(path) as f:
        return [x.strip().lower() for x in f if x.strip()]


def load_csv_ids(path):
    raw = open(path).read().replace("\n", "")
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


def pool_from_datafolder(datafolder):
    files = glob.glob(os.path.join(datafolder, "*.property.pvar"))
    return sorted({os.path.basename(f).split(".")[0].lower() for f in files})


def clan_holdout(cdk2_ids, clan_df_path):
    """Return the union of all PDB ids in any clan containing a CDK2 id."""
    df = pickle.load(open(clan_df_path, "rb"))
    cdk2_set = set(cdk2_ids)
    holdout = set()
    n_clans = 0
    for _, row in df.iterrows():
        members = {str(x).lower() for x in row["PDBIDList"]}
        if members & cdk2_set:
            holdout |= members
            n_clans += 1
    return holdout, n_clans


def paper_kfold_holdout(ignore_ids, clan_df_path, seed=42):
    """Reproduce the repo's make_kfold.py --ignorefile IsRemoved logic EXACTLY.

    A clan is flagged IsRemoved if its PDBIDList shares ANY structure with the
    ignore list (the 438-member CDK2 90%-identity set). Every structure in a
    removed clan becomes the held-out (CDK2) validation pool; the remaining
    clans are the training pool. This matches
        make_kfold.py --clanfile ClanGraph_90_df.pkl \
                      --ignorefile cdk2_1h00_90identity.txt --seed 42
    so the CDK2 leave-out is identical to the FeatureDock paper's protocol.

    Note: the IsRemoved holdout is fully deterministic (set intersection); no RNG
    is involved. The `seed` in make_kfold.py only affects the k-fold shuffle of
    the *remaining* clans, which is not part of the train/val holdout we produce.
    The parameter is kept for signature parity but does not change this result.
    """
    df = pickle.load(open(clan_df_path, "rb"))
    ignore = set(ignore_ids)
    removed, kept = set(), set()
    n_removed_clans = 0
    for _, row in df.iterrows():
        members = {str(x).lower() for x in row["PDBIDList"]}
        if members & ignore:        # IsRemoved == True
            removed |= members
            n_removed_clans += 1
        else:
            kept |= members
    return removed, kept, n_removed_clans


def paper_cv_split(ignore_ids, clan_df_path, seed=42, ratio=0.1):
    """Full FeatureDock-paper three-way split at the CLAN level, matching
    train_main.py lines 65-72 exactly:

      test  = clans flagged IsRemoved by the CDK2 ignore-list (the '-1' fold)
      val   = a random `ratio` (10%) of the REMAINING clans (np.random, seed 42)
      train = the rest of the remaining clans

    Returns (train_pdbs, val_pdbs, test_pdbs, stats) as sets of lowercase ids.
    """
    import numpy as np
    df = pickle.load(open(clan_df_path, "rb"))
    ignore = set(ignore_ids)

    # membership per clan
    clan_members = {}
    test_clans, rest_clans = set(), set()
    for _, row in df.iterrows():
        cid = row["Structure_Clan_ID"]
        members = {str(x).lower() for x in row["PDBIDList"]}
        clan_members[cid] = members
        if members & ignore:          # IsRemoved -> test (the -1 fold)
            test_clans.add(cid)
        else:
            rest_clans.add(cid)

    # random 10% of the remaining clans -> validation (seed matches train_main.py)
    np.random.seed(seed)
    rest_sorted = sorted(rest_clans)
    n_val = int(np.ceil(ratio * len(rest_sorted)))
    val_clans = set(np.random.choice(rest_sorted, n_val, replace=False))
    train_clans = rest_clans - val_clans

    def collect(clans):
        out = set()
        for c in clans:
            out |= clan_members[c]
        return out

    train_pdbs, val_pdbs, test_pdbs = collect(train_clans), collect(val_clans), collect(test_clans)
    stats = dict(test_clans=len(test_clans), val_clans=len(val_clans),
                 train_clans=len(train_clans), n_val_clans_target=n_val)
    return train_pdbs, val_pdbs, test_pdbs, stats


def main():
    ap = argparse.ArgumentParser(description="CDK2-as-validation split for FeatureDock.")
    ap.add_argument("--datafolder", required=True,
                    help="folder of <pid>.property.pvar files (the trainable pool)")
    ap.add_argument("--datadir", default=os.path.join(os.path.dirname(__file__), "..", "..", "data"),
                    help="FeatureDock data/ dir with the CDK2 lists + clan graph")
    ap.add_argument("--cdk2-scope", choices=["crystals", "homologs", "clan", "paper", "paper_cv"],
                    default="paper",
                    help="how to define the CDK2 hold-out. 'paper' (default) reproduces the "
                         "repo's make_kfold.py --ignorefile IsRemoved protocol exactly (2-way: "
                         "train + CDK2-val). 'paper_cv' is the paper's full 3-way split: CDK2 as "
                         "TEST (-1 fold), random 10%% of remaining clans as VAL, rest as TRAIN.")
    ap.add_argument("--seed", type=int, default=42,
                    help="random seed, matches make_kfold.py / train_main.py default (42)")
    ap.add_argument("--val-ratio", type=float, default=0.1,
                    help="paper_cv only: fraction of remaining clans used as validation")
    ap.add_argument("--out-train", default="train_pids.txt")
    ap.add_argument("--out-val", default="val_pids.txt")
    ap.add_argument("--out-test", default="test_pids.txt",
                    help="paper_cv only: CDK2 test-set PID list")
    args = ap.parse_args()

    # ---- paper_cv: full 3-way clan split (train / random-val / CDK2-test) ----
    if args.cdk2_scope == "paper_cv":
        pool = pool_from_datafolder(args.datafolder)
        if not pool:
            raise SystemExit(f"No .property.pvar files found in {args.datafolder}")
        homologs = load_csv_ids(os.path.join(args.datadir, "cdk2_1h00_90identity.txt"))
        crystals = load_lines(os.path.join(args.datadir, "cdk2_in_PDBBind.txt"))
        tr, va, te, stats = paper_cv_split(
            homologs, os.path.join(args.datadir, "ClanGraph_90_df.pkl"),
            seed=args.seed, ratio=args.val_ratio)
        poolset = set(pool)
        train = sorted(tr & poolset); val = sorted(va & poolset); test = sorted(te & poolset)
        # sanity: three disjoint sets, CDK2 only in test
        assert not (set(train) & set(val)), "train/val overlap!"
        assert not (set(train) & set(test)), "train/test overlap!"
        assert not (set(val) & set(test)), "val/test overlap!"
        leaked = (set(train) | set(val)) & (set(crystals) | set(homologs))
        assert not leaked, f"CDK2 leaked into train/val: {sorted(leaked)[:5]}"
        for path, ids in ((args.out_train, train), (args.out_val, val), (args.out_test, test)):
            open(path, "w").write("\n".join(ids) + "\n")
        print(f"[split] paper_cv (seed={args.seed}, val_ratio={args.val_ratio}): "
              f"clans test={stats['test_clans']} val={stats['val_clans']} train={stats['train_clans']}")
        print(f"[split] structures: train={len(train)} val={len(val)} test(CDK2)={len(test)}")
        print(f"[split] wrote {args.out_train}, {args.out_val}, {args.out_test}")
        return

    pool = pool_from_datafolder(args.datafolder)
    if not pool:
        raise SystemExit(f"No .property.pvar files found in {args.datafolder}")

    crystals = load_lines(os.path.join(args.datadir, "cdk2_in_PDBBind.txt"))
    homologs = load_csv_ids(os.path.join(args.datadir, "cdk2_1h00_90identity.txt"))
    cdk2_union = sorted(set(crystals) | set(homologs))

    if args.cdk2_scope == "crystals":
        val_target = set(crystals)
    elif args.cdk2_scope == "homologs":
        val_target = set(crystals) | set(homologs)
    elif args.cdk2_scope == "clan":
        holdout, n_clans = clan_holdout(cdk2_union,
                                        os.path.join(args.datadir, "ClanGraph_90_df.pkl"))
        val_target = holdout
        print(f"[split] clan scope: {n_clans} clan(s) contain a CDK2 id "
              f"-> {len(holdout)} structures held out")
    else:  # paper -- exact make_kfold.py --ignorefile IsRemoved reproduction
        removed, kept, n_removed = paper_kfold_holdout(
            homologs, os.path.join(args.datadir, "ClanGraph_90_df.pkl"), seed=args.seed)
        val_target = removed
        print(f"[split] paper scope (seed={args.seed}): ignore-list={len(homologs)} CDK2 homologs "
              f"-> {n_removed} clan(s) IsRemoved -> {len(removed)} structures held out, "
              f"{len(kept)} kept for training")

    # Validation = CDK2 target intersected with what we actually have featurized.
    val = sorted(val_target & set(pool))
    train = sorted(set(pool) - val_target)   # remove ALL CDK2-target ids from train

    # sanity: no overlap, and the CDK2 crystals are never in train
    assert not (set(train) & set(val)), "train/val overlap!"
    leaked = set(train) & (set(crystals) | set(homologs))
    assert not leaked, f"CDK2 ids leaked into train: {sorted(leaked)[:5]}"

    with open(args.out_train, "w") as f:
        f.write("\n".join(train) + "\n")
    with open(args.out_val, "w") as f:
        f.write("\n".join(val) + "\n")

    print(f"[split] pool={len(pool)}  train={len(train)}  val(CDK2, {args.cdk2_scope})={len(val)}")
    print(f"[split] wrote {args.out_train} and {args.out_val}")
    if not val:
        print("[split] WARNING: 0 CDK2 structures in the pool -- did you featurize them? "
              "CDK2 must be featurized too (it is the validation set).")


if __name__ == "__main__":
    main()
