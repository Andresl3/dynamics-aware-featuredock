# Dynamics-aware FeatureDock — augmentation ① code

Custom code for adding a per-residue **Dyna-1 µs–ms motion channel** to
FeatureDock's grid-point features (6×80 → 6×81) and training baseline vs
dynamics-aware models on PDBBind v2020 with **CDK2 held out as validation**.

## What's here

| File | Goes into (in cloned FeatureDock/Dyna-1) | Purpose |
|------|------------------------------------------|---------|
| `curate_dataset/featurize_dyna1_channel.py` | `featuredock/src/curate_dataset/` | Appends Dyna-1 `p_exchange` as the 81st per-shell property |
| `curate_dataset/make_cdk2_split.py` | `featuredock/src/curate_dataset/` | Train/val split: all PDBBind → train, CDK2 → validation |
| `curate_dataset/create_voxels_and_landmarks.py` | `featuredock/src/curate_dataset/` | **Patched** — relaxed protein+ligand loaders (recovers structures RDKit rejects on valence errors) |
| `models/train_dynamics_aware.py` | `featuredock/src/models/` | Training script taking explicit PID lists + `--feature_per_shell` |
| `models/parse_config.py` | `featuredock/src/models/` | **Patched** — makes `feature_per_shell`/`num_shells` configurable (was hardcoded 80/6) |
| `dyna1/precompute_dyna1.py` | `Dyna-1/` | Batch Dyna-1 inference (model loaded once) → one CSV per protein |

The Colab notebook is in `../notebooks/dynamics_aware_featuredock_colab.ipynb`.

## How to run on Colab (your friend's account)

1. **Clone or pull this repo** anywhere.
2. On Google Drive, create a project folder and inside it a `code/` subfolder;
   upload the 6 `.py` files above into `code/` (the notebook copies them into
   the freshly-cloned FeatureDock tree at run time — this is how our changes
   survive the repo clone).
3. Also upload your PDBBind v2020 archive to that Drive project folder.
4. Open `notebooks/dynamics_aware_featuredock_colab.ipynb` in Colab, set the
   runtime to **GPU (T4)**, and set `WORK` in §1 to your Drive project folder.
5. Run cells top-to-bottom. §0–§7 = setup, §8 = preprocessing (long, resumable),
   §9–§11 = split + train both arms + compare on CDK2.

See the top of the notebook for the **"If Colab disconnects"** resume steps, and
`../README_dynamics_aware.md` for the channel layout and how to import the
trained checkpoints back into the repo.

## Pipeline in one line

```
sequence → [ESM-2 inside Dyna-1] → p_exchange per residue
        → featurize_dyna1_channel.py → motion on pocket grid points
        → FeatureDock trained with that extra channel (6×81)
```
