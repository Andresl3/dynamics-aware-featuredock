# Running Dynamics-aware FeatureDock on an HPC cluster (SLURM)

Headless, GPU-ready version of the full pipeline — no notebook, no Colab limits.
Everything here assumes a **SLURM** scheduler; adapt the `#SBATCH` lines to your
site (partition, account, module names).

## Files

| File | What it does |
|------|--------------|
| `setup_env.sh` | One-time: builds the conda env, clones the two tool repos, overlays our patched code, unpacks FEATURE, downloads Dyna-1 weights |
| `preprocess.py` | Standalone version of notebook §8 — the 6-stage per-structure pipeline, shardable + resumable |
| `run_preprocess.slurm` | Job array that runs `preprocess.py` across N shards (parallel) |
| `run_train.slurm` | Builds the CDK2 split, trains baseline (80) and +Dyna-1 (81), one GPU job |

## Step 0 — get the code and data onto the cluster

```bash
cd $HOME
git clone https://github.com/natesana/dynamics-aware-featuredock.git
cd dynamics-aware-featuredock
```

**PDBBind is NOT in the repo** (it's gigabytes and requires registration). Copy
your own PDBBind v2020 to the cluster (scp/rsync/Globus) and note its path — the
extracted tree with `<pid>/<pid>_protein.pdb` + `<pid>_ligand.sdf` per complex,
either flat or nested as `P-L/<year>/<pid>/`.

## Step 1 — build the environment (login node, once)

```bash
bash hpc/setup_env.sh
```

**Before running it, pick the right GPU PyTorch build** — open `setup_env.sh`
and set the CUDA wheel index to match `nvidia-smi` on your GPU nodes (the file
defaults to CUDA 12.1). Everything else (numpy<2 pin, rdkit, prolif, Dyna-1
deps, FEATURE chmod, weights download) is handled for you.

## Step 2 — preprocess (GPU job array)

Edit the paths at the top of `run_preprocess.slurm` (`ROOT`, `PDBBIND_DIR`,
`OUT_DIR`) and the partition/account, then:

```bash
# smoke test first: 30 structures, one task
sbatch --array=1-1 hpc/run_preprocess.slurm    # (add --limit 30 in the script)

# full run: 10 shards in parallel
sbatch hpc/run_preprocess.slurm
```

Each array task writes to a shared `$OUT_DIR` (`pvar_80/`, `pvar_81/`, `dyna1_csv/`,
labels). Resumable: re-submitting skips finished structures. Put `$OUT_DIR` on
**scratch/fast storage** — it holds thousands of small files.

**Sharding math:** `--array=1-10` splits the ~5,300 refined complexes into 10
parallel tasks (~530 each). Increase the array size for more parallelism / less
wall time per task; each still needs one GPU for the Dyna-1 inference step.

## Step 3 — train + compare

After all preprocessing shards finish:

```bash
sbatch hpc/run_train.slurm
```

Trains both arms with identical settings (only the feature width differs: 80 vs
81) on the CDK2-as-validation split, saving checkpoints + `history.json` under
`$OUT_DIR/results/`. Compare the two `*_history.json` (val loss / MCC) to see
whether the Dyna-1 motion channel helps on CDK2.

## Notes

- **numpy is pinned `<2`** — Dyna-1's `biotite==0.41.2` needs it. Don't upgrade.
- **Dyna-1 CSVs are cached** in `$OUT_DIR/dyna1_csv/`; the model loads per
  structure via the stock script. To load the model ONCE for all structures
  (faster), run `python Dyna-1/precompute_dyna1.py --pdbbind-dir ... --save-dir
  $OUT_DIR/dyna1_csv --refined-list featuredock/data/pdblist.txt` before the
  array job — `preprocess.py` then reuses those CSVs.
- **FEATURE** is a Linux binary shipped in the repo; `setup_env.sh` unpacks it
  and sets the execute bit (the fix for the `Permission denied` we hit on Colab).
- **CDK2** is held out as validation only — never in training. `run_train.slurm`
  uses `--cdk2-scope paper --seed 42`, which reproduces the repo's
  `make_kfold.py --ignorefile` `IsRemoved` protocol exactly (any clan sharing a
  structure with the 438-member CDK2 90%-identity list is pulled out → 18
  structures held out, 4497 kept, zero leakage).
- **Warm-start (optional):** set `WARM_START` at the top of `run_train.slurm` to
  one of FeatureDock's shipped checkpoints
  (`results/vit_20/HeavyAtomsite_transformer_20_seed*.torch`) to start from
  pretrained weights. Matching layers load; the `norm_layer` that changes shape
  with the Dyna-1 channel (80→81) is reinitialized automatically. Leave empty to
  train from scratch.
