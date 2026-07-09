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


def main():
    ap = argparse.ArgumentParser(description="CDK2-as-validation split for FeatureDock.")
    ap.add_argument("--datafolder", required=True,
                    help="folder of <pid>.property.pvar files (the trainable pool)")
    ap.add_argument("--datadir", default=os.path.join(os.path.dirname(__file__), "..", "..", "data"),
                    help="FeatureDock data/ dir with the CDK2 lists + clan graph")
    ap.add_argument("--cdk2-scope", choices=["crystals", "homologs", "clan", "paper"],
                    default="paper",
                    help="how to define the CDK2 hold-out. 'paper' (default) reproduces the "
                         "repo's make_kfold.py --ignorefile IsRemoved protocol exactly.")
    ap.add_argument("--seed", type=int, default=42,
                    help="random seed, matches make_kfold.py default (42) for reproducibility")
    ap.add_argument("--out-train", default="train_pids.txt")
    ap.add_argument("--out-val", default="val_pids.txt")
    args = ap.parse_args()

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
