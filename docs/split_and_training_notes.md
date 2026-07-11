# Dynamics-aware FeatureDock — data split & training notes

Paste-ready notes for the shared Google Doc. Covers how the train/val split is
regenerated (matching the FeatureDock paper), the CDK2 leave-out, and warm-start
from the pretrained checkpoints. Written to match the protocol Andres described.

---

## 1. The split basis (regenerated, not downloaded)

The split is regenerated from the shipped cluster graph — no split file is
downloaded. Everything needed ships in the FeatureDock repo:

- `data/ClanGraph_90_df.pkl` — 1,326 clans with their PDB-ID lists (columns
  `Structure_Clan_ID`, `PDBIDList`). This is the split basis.
- `data/labeled_pdblist.txt` — 4,516 curated PDB IDs that survived preprocessing.
- `data/cdk2_in_PDBBind.txt` — 18 CDK2 crystal structures in PDBBind.
- `data/cdk2_1h00_90identity.txt` — the 438-member CDK2 90%-identity cluster.

Splits are done at the **clan level** (not per-structure) so homologous
structures never straddle the train/val boundary.

## 2. Two split modes

### (a) Paper random 10% clan-level fold (seed 42)
The FeatureDock paper's own scheme: hold out a random 10% of clans as validation,
the rest train. Reproduced with the fixed seed from the train script:

```python
import pickle, numpy as np
df = pickle.load(open("data/ClanGraph_90_df.pkl", "rb"))
foldids = df['Structure_Clan_ID'].unique().tolist()
np.random.seed(42)                       # seed from step2_2 / train script
ratio = 0.1
val   = sorted(np.random.choice(sorted(foldids),
                                int(np.ceil(ratio*len(foldids))), replace=False))
train = sorted(set(foldids) - set(val))
val_pdbs   = [p for _, r in df.iterrows() if r.Structure_Clan_ID in val   for p in r.PDBIDList]
train_pdbs = [p for _, r in df.iterrows() if r.Structure_Clan_ID in train for p in r.PDBIDList]
```

### (b) CDK2 leave-out (make_kfold.py --ignorefile)
For the CDK2 leave-out, use the repo's `make_kfold.py --ignorefile
data/cdk2_1h00_90identity.txt`: any clan sharing a structure with the 438-member
CDK2 90%-identity list is flagged `IsRemoved` and pulled out of training; the
rest go to k-fold.

Our `make_cdk2_split.py --cdk2-scope paper --seed 42` reproduces this `IsRemoved`
logic exactly. Verified on the real clan graph:
- 438 CDK2 homologs → **1 clan flagged IsRemoved** → **18 structures held out,
  4497 kept**, zero train/val overlap, all 18 CDK2 crystals in the held-out set.

## 3. Warm-start from pretrained checkpoints

The repo ships pretrained transformer weights at
`results/vit_20/HeavyAtomsite_transformer_20_seed{0,1,10,42,1234}`. You can
warm-start the Dyna-1 model from these.

**Refinement to Andres's note:** the 6×80 → 6×81 change does require
reinitializing one layer, but it is **not** the "first transformer projection
layer" (`word2dense`, which projects the 6-shell axis and is unchanged). The
layer that changes shape is the per-property normalization
`norm_layer = nn.BatchNorm2d(feature_per_shell)` (80 → 81). Our
`train_dynamics_aware.py --warm-start <ckpt>` loads every shape-matching tensor
and reinitializes only that one automatically:
- loads 90 tensors, reinitializes 4 (`bert.norm_layer.{weight,bias,running_mean,running_var}`).

## 4. Commands (HPC / SLURM)

```bash
# Split reproducing the paper CDK2 leave-out (seed 42):
python src/curate_dataset/make_cdk2_split.py \
    --datafolder $OUT81 --datadir featuredock/data \
    --cdk2-scope paper --seed 42 \
    --out-train train_pids.txt --out-val val_pids.txt

# Train, optionally warm-starting from a pretrained checkpoint:
python src/models/train_dynamics_aware.py \
    --modeltype transformer --feature_per_shell 81 --datafolder $OUT81 \
    --train-pids train_pids.txt --val-pids val_pids.txt \
    --warm-start featuredock/results/vit_20/HeavyAtomsite_transformer_20_seed42.torch \
    --outfolder results/dyna1_81 --steps 1000 --lr 1e-3 --use_gpu
```

## 5. Two split modes now available

**How the paper actually splits** (from `train_main.py` lines 65-72): it builds
THREE clan-level sets — CDK2 (the `IsRemoved` `-1` fold) as **test**, a random
10% of the remaining clans as **validation**, and the rest (~90%) as **training**.

`make_cdk2_split.py` supports both:

- `--cdk2-scope paper` (2-way, our project default): train on ALL non-CDK2
  refined structures, CDK2 as the sole validation set. Uses the paper's CDK2
  `IsRemoved` leave-out exactly, but collapses the paper's train+val into one
  training pool (no separate random val fold). Verified on the real clan graph
  (this window): 438 homologs → 1 clan IsRemoved → **18 held out, 4497 kept**,
  zero overlap, 18/18 CDK2 crystals in the held-out set.

- `--cdk2-scope paper_cv` (3-way, matches the paper exactly): CDK2 as **test**,
  random 10% of remaining clans as **val**, rest as **train**. Verified on the
  real clan graph (this window): 1 test clan / 133 val clans / 1192 train clans
  → **train=4144, val=353, test(CDK2)=18**, all three disjoint, zero CDK2 leakage,
  and the 133 val-clan count matches the paper formula ceil(0.1×(1326−1)).

## 6. Future direction (from Andres's note)
> "incorporate E3-equivariant diffusion models to generate binding positions
> based on the probability density envelopes."

Aspirational next step, only meaningful after FeatureDock is trained — a
generative pose sampler on top of the predicted probability envelopes. Not part
of the current build.
