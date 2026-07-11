# Getting the large files (weights + Dyna-1 CSVs)

Git does **not** carry the big binaries — they are gitignored on purpose
(`.torch` weights, PDBBind, `.pvar`/`.voxels.pkl`/`.sdf` data). This file says
where to get them and where to put them.

You need these ONLY if you want to skip a compute step:
- **Dyna-1 CSVs** — to skip the GPU precompute (step 3 of REPRODUCE.md).
- **Trained weights** — to TEST without retraining. If you are training from
  scratch you do NOT need these; you produce them yourself in step 5.

---

## 1. Dyna-1 precomputed CSVs  (`dyna1_csv.tar.gz`, ~16 MB)

One CSV per PDB id (`position,residue,p_exchange`), ~5,297 files. This is the
output of the multi-hour Dyna-1 GPU precompute; having it lets you jump straight
to preprocessing.

**Share it as a GitHub Release asset** (a 16 MB tarball is fine for a Release,
but must NEVER be a normal committed file):
```bash
# producer (has the tarball on the cluster):
gh release create dyna1-csv-v1 dyna1_csv.tar.gz \
    -t "Dyna-1 precomputed CSVs" -n "p_exchange per residue for the refined pool"
# if gh is unavailable, upload dyna1_csv.tar.gz to the Release via the web UI,
# or drop it in a shared Drive folder and paste the link here.
```

**Consumer:**
```bash
# download the asset (web UI, or: gh release download dyna1-csv-v1)
mkdir -p $OUT_DIR/dyna1_csv
tar -xzf dyna1_csv.tar.gz -C $OUT_DIR/dyna1_csv
```

---

## 2. Trained model checkpoints  (`.torch`, ~2 MB each)

Produced by `train_dynamics_aware.py`. Each checkpoint stores its own
architecture (`ckpt['args']`) so the eval scripts rebuild the right model.

| file | arm | how made |
|---|---|---|
| `results/baseline80/baseline80_final_params.torch`       | from-scratch 6x80 | run_train.slurm |
| `results/dyna1_81/dyna1_81_final_params.torch`           | from-scratch 6x81 | run_train.slurm |
| `results/baseline80_warm/baseline80_warm_final_params.torch` | warm 6x80 (20-block) | run_train_warmstart.slurm |
| `results/dyna1_81_warm/dyna1_81_warm_final_params.torch`     | warm 6x81 (20-block) | run_train_warmstart.slurm |

Each is only ~2 MB, so a **Release asset** or Drive folder works. Put them back
under `$OUT_DIR/results/<name>/` with the exact filenames above, and the
`run_evaluate*.slurm` / `run_rmsd_*.slurm` scripts find them unchanged.

The warm arm also needs FeatureDock's **pretrained 20-block checkpoint** to
fine-tune FROM:
`featuredock/results/vit_20/HeavyAtomsite_transformer_20_seed42/HeavyAtomsite_transformer_20_seed42_best_checkpoint_params.torch`
— this ships inside the `featuredock/` tool repo that `setup_hackathon_mamba.sh`
clones, so you get it automatically.

---

## Rule of thumb

- **Code / scripts / ID lists** -> git (this repo).
- **Anything `.torch`, `.tar.gz`, or PDBBind data** -> Release asset or Drive,
  never a git commit. If you ever see a multi-MB binary in `git status`, it is
  gitignored for a reason — don't `git add -f` it.
