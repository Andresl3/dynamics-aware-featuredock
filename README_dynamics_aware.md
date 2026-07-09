# Dynamics-aware FeatureDock — Augmentation ① (Dyna-1 dynamics channel)

This adds a per-residue **µs–ms conformational-dynamics channel** (from
[Dyna-1](https://github.com/WaymentSteeleLab/Dyna-1)) to FeatureDock's grid-point
FEATURE tensor, taking each pocket from **6×80 → 6×81** features, then retrains
FeatureDock on **all of PDBBind v2020 with CDK2 held out as the validation set**.

> **Where training runs:** the FEATURE program and DSSP are Linux binaries, and
> full training needs a GPU — so training runs on **Google Colab**, not a Mac.
> The local machine is used only to build and unit-test the new code.

---

## New / changed files

| File | Purpose |
|------|---------|
| `src/curate_dataset/featurize_dyna1_channel.py` | Append the Dyna-1 motion channel to a pocket tensor: `(N,480) → (N,486)`. Aggregates per-residue `p_exchange` into each of the 6 FEATURE shells, mirroring FEATURE's own shell aggregation. |
| `src/curate_dataset/make_cdk2_split.py` | Build `train_pids.txt` / `val_pids.txt`: all PDBBind → train, CDK2 → validation. Three hold-out scopes (`crystals` / `homologs` / `clan`), default `homologs` (leakage-safe). |
| `src/models/parse_config.py` | **Patched.** New `--feature_per_shell` (80 baseline / 81 +Dyna-1) and `--num_shells`, threaded into all three model builders (transformer / cnn / fnn). Default 80 → baseline behavior unchanged. |
| `src/models/train_dynamics_aware.py` | Train with an **explicit** CDK2-validation split (vs. the stock random clan-fold split). Reuses FeatureDock's own dataset/model/loss. Trains baseline (80) and +Dyna-1 (81) identically. |
| `notebooks/dynamics_aware_featuredock_colab.ipynb` | The full GPU pipeline end-to-end on Colab. |

---

## The channel layout (6×80 → 6×81)

FeatureDock describes each grid point with the Altman FEATURE vector: **6
concentric shells** (1.25 Å thick) × **80 properties** = a flat `(N, 480)`
tensor. The model reshapes it to `(N, 6, 80)`.

The Dyna-1 channel adds **one property per shell** — the aggregated `p_exchange`
of residues whose atoms fall in that shell — inserted as the **81st feature of
each shell**:

```
native flat: [s0f0..s0f79 | s1f0..s1f79 | ...]                    (480)
+Dyna-1:     [s0f0..s0f79 s0_motion | s1f0..s1f79 s1_motion | ...] (486)
```

So `feature_batch.view(-1, 6, 81)[:, :, -1]` is exactly the motion channel. The
native 80 properties are preserved bit-for-bit; the classifier head is unchanged
(only the shell-projection input widens by 1).

**Validated locally** on the shipped CDK2 example (`1b38`, 3,163 grid points):
`(3163,480) → (3163,486)`, all 290 residues mapped, and both an 80-wide and
81-wide `BertSentClassifier` run forward+backward cleanly.

---

## Running the full training (Google Colab)

1. Open `notebooks/dynamics_aware_featuredock_colab.ipynb` in Colab; set
   **Runtime → GPU**.
2. Upload the 4 new/changed `.py` files to `MyDrive/dynamics_aware_featuredock/code/`
   (or `git pull` your fork inside the notebook).
3. Download the **PDBBind v2020 refined set** (free registration at
   http://www.pdbbind.org.cn/) and put it on Drive; set `PDBBIND_DIR`.
4. Run the cells top to bottom. The notebook:
   - unpacks the FEATURE binary + DSSP,
   - downloads Dyna-1 ESM-2 weights from `gelnesr/Dyna-1`,
   - for **every** structure: voxels → FEATURE (`pvar_80/`) → Dyna-1 → 6×81
     (`pvar_81/`) → occupancy labels,
   - builds the CDK2-validation split,
   - trains **baseline (80)** and **+Dyna-1 (81)**,
   - writes checkpoints, `*_history.json`, and `compare_cdk2.png` to Drive.

**CDK2 is validation only** — it is removed from the training pool (with its 90%
identity homologs) so validation measures generalization to the worksheet's
headline flexible target.

---

## Importing Colab-trained results back into the repo

After training, `MyDrive/dynamics_aware_featuredock/results/` contains:

```
results/
  baseline80/  baseline80_final_params.torch   baseline80_history.json   baseline80_step*.torch
  dyna1_81/    dyna1_81_final_params.torch     dyna1_81_history.json     dyna1_81_step*.torch
  compare_cdk2.png
```

1. **Download** that `results/` folder and drop it into the repo at
   `featuredock/results/`.
2. **Keep large weights out of git** — they're already covered by the
   project `.gitignore` (`*.torch`, `*.pt`, `results/`). Commit the
   `*_history.json` and `compare_cdk2.png` (small) if you want the metrics
   tracked; keep the multi-MB `.torch` checkpoints on Drive / a release asset.
3. **Load a checkpoint** to predict / evaluate on CDK2:

   ```python
   import torch, sys; sys.path.insert(0, "src")
   from models.transformer_models import BertSentClassifier
   ckpt = torch.load("results/dyna1_81/dyna1_81_final_params.torch", map_location="cpu")
   fps  = ckpt["args"]["feature_per_shell"]          # 81 for the dynamics-aware model
   model = BertSentClassifier(n_class=2, num_shells=6, feature_per_shell=fps,
                              hidden_size=64, intermediate_size=64, num_hidden_layers=5,
                              num_attention_heads=2, max_position_embeddings=100,
                              layer_norm_eps=1e-12, hidden_dropout_prob=0.1,
                              attention_probs_dropout_prob=0.1, option="finetune")
   model.load_state_dict(ckpt["model_state_dict"]); model.eval()
   ```

   Feed it a `(N, 486)` tensor built by `featurize_dyna1_channel.py` (use the
   matching **486** width — an 80-wide baseline checkpoint takes **480**).
4. **Reproduce the paper's metrics** (pose-RMSD ≤ 2 Å success, strong-vs-weak
   AUC) on the CDK2 validation set with the repo's downstream tools
   (`src/application/predict_main.py`, `src/application/plot_predicted_poses.py`),
   pointing them at the loaded checkpoint and the CDK2 `pvar_81/` tensors.

---

## Baseline vs +Dyna-1 (what to compare)

Both models are trained identically (same split, steps, LR, sampler); the only
difference is the extra channel. Compare on the **CDK2 validation set**:

- validation loss / MCC learning curves (`compare_cdk2.png`),
- pose-RMSD success rate (≤ 2 Å),
- strong- vs weak-binder discrimination (AUC / KL), stratified by pocket
  flexibility — the mobile G-loop / Tyr15 region is where the dynamics channel
  is expected to help most.

> Until the Colab run completes, no trained metrics exist — the local outputs
> (`fig_step1_dyna1_channel.png`, shape/forward-backward checks) validate the
> **code path**, not model performance. The `dyna1_cdk2_pexchange_SYNTHETIC.csv`
> used locally is synthetic; the real `p_exchange` comes from Dyna-1 on Colab.
