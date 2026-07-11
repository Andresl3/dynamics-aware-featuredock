# Reproduce the Dynamics-Aware FeatureDock pipeline

A linear runbook to go from a fresh clone to trained models + evaluation,
matching exactly what the team ran. Everything here is code you already have in
this repo; the three large inputs (tool repos, PDBBind, Dyna-1 CSVs) are pulled
separately because they are too big / not ours to redistribute.

Target environment: a SLURM cluster with a V100 (32 GB) GPU. Steps 3b, 4, 5 use
the GPU; the rest are CPU.

---

## 0. What the augmentation is (one paragraph)

FeatureDock predicts a per-grid-point binding-site "occupancy" from a 6-shell x
80-property tensor (6x80 = 480 features per voxel). We add ONE extra property
per shell — the Dyna-1 predicted us-ms conformational-exchange probability for
the nearest residue — making it 6x81 = 486. Everything downstream (training,
posing, RMSD eval) runs twice: a `baseline` arm (6x80) and a `dyna1` arm (6x81).
The scientific question is whether the dynamics channel improves binding-site
or pose prediction. (Result so far on CDK2 held-out: no measurable effect.)

---

## 1. Clone + environment

```bash
git clone https://github.com/natesana/dynamics-aware-featuredock.git
cd dynamics-aware-featuredock
bash setup_hackathon_mamba.sh      # clones the 3 tool repos + builds the conda env
```

`setup_hackathon_mamba.sh` clones **featuredock/**, **Dyna-1/**, and
**protpardelle-1c/** into the repo root (they are gitignored — never committed)
and creates the conda env. Note the env name it makes; every SLURM script has a
line `ENV_NAME="dynafeat"` near the top — **set that to your env name** (on our
cluster it is `dynafeat`).

Every SLURM script also uses absolute paths for our cluster
(`/scratch/mani.na/...`). **Edit `ROOT` / `OUT_DIR` at the top of each script to
your own scratch path** before submitting.

---

## 2. Get PDBBind v2020 (refined set)

Register (free) at http://www.pdbbind.org.cn and download the **refined set**.
Untar it, then point the pipeline at it:

```bash
export PDBBIND_DIR=/your/path/to/PDBbind_v2020_refined/refined-set
```

The refined pool we used is `featuredock/data/pdblist.txt` (5,316 IDs;
5,299 survive preprocessing).

---

## 3. Get the Dyna-1 channel  (choose 3a OR 3b)

This is the ONE expensive precompute. Pick the cheap path if you can.

### 3a. (recommended) Download the precomputed CSVs — skips the GPU step
Ask a teammate for `dyna1_csv.tar.gz` (~16 MB; shared as a GitHub Release asset
or Drive link — see docs/HOW_TO_GET_WEIGHTS.md). Then:

```bash
mkdir -p $OUT_DIR/dyna1_csv
tar -xzf dyna1_csv.tar.gz -C $OUT_DIR/dyna1_csv
# one CSV per PDB id: position,residue,p_exchange
```

### 3b. Regenerate them yourself (GPU, hours)
```bash
sbatch hpc/run_dyna1_precompute.slurm    # runs code/dyna1/precompute_dyna1.py
# Dyna-1 (ESM-2 backbone) inference over all refined structures -> one CSV each.
# ~5,297 succeed; ~10 fail with CUDA OOM on very long chains (safe to skip).
```

---

## 4. Preprocess -> feature tensors  (GPU)

```bash
sbatch hpc/run_preprocess.slurm          # runs hpc/preprocess.py
```
Produces, under `$OUT_DIR/`:
- `pvar_80/{pid}.property.pvar`  — baseline 6x80 tensors
- `pvar_81/{pid}.property.pvar`  — Dyna-1-augmented 6x81 tensors
- `voxels/{pid}.voxels.pkl`, `het/{pid}_ligand.sdf`, and the occupancy labels
Sanity after it finishes: `pvar_80 ~5307`, `pvar_81 ~5299`, `labels ~5299`.

---

## 5. Split + train  (GPU)

The split and training are driven by `hpc/run_train.slurm`, which calls
`make_cdk2_split.py` then `train_dynamics_aware.py` for both arms.

- **Split**: `--cdk2-scope paper_cv` reproduces the paper's clan-based CV — CDK2's
  clan is the held-out TEST set, a random 10% of the remaining clans is VAL, the
  rest is TRAIN. Result: train=4128, val=353, test(CDK2)=18.
- **From-scratch training**: 20 epochs, ~214 s/epoch on a V100 (~1.2 h/arm).
  Baseline writes `results/baseline80/`, Dyna-1 writes `results/dyna1_81/`.

```bash
sbatch hpc/run_train.slurm               # from-scratch, both arms
```

**Warm-start (optional)**: fine-tune from FeatureDock's pretrained 20-block
checkpoint instead of random init. Both arms MUST be built `--n_blocks 20` to
match the checkpoint. Lower `--n_structs` to 4 + set
`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` to fit 32 GB.
```bash
sbatch hpc/run_train_warmstart.slurm     # -> results/baseline80_warm/, results/dyna1_81_warm/
```

---

## 6. Evaluate

**Occupancy** (binding-site prediction; fast, one forward pass/structure):
```bash
sbatch hpc/run_evaluate.slurm            # CDK2 head-to-head -> cdk2_summary.csv
```

**Pose RMSD** (the worksheet's PRIMARY metric; posing is CPU-bound, slow):
```bash
sbatch hpc/run_rmsd_full18.slurm         # 18 CDK2 structs, 500 rotations, top-4 + oracle
```
`evaluate_cdk2_rmsd.py` reports per structure: `top1` (best-scored pose),
`top4` (best RMSD among top-4 scored — the paper-comparable number; paper CDK2 =
2.4 A), and `oracle` (min RMSD over all restarts — a best-case diagnostic, NOT a
benchmark number) plus the oracle pose's score and its rank in the score list.

**Dynamics-target screen** (p38a / HSP90a / CA-II; illustrative, train-set):
```bash
sbatch hpc/run_occupancy_screen.slurm    # full n, both regimes
sbatch hpc/run_rmsd_screen.slurm         # array 0-2, n=20/target, both regimes
```
Reads the ID lists in `hpc/target_pids/` (shipped in the repo).

---

## Notes / gotchas we hit

- **conda in batch jobs**: a non-interactive SLURM shell has no `conda` function,
  so `conda activate` fails with "Run 'conda init'...". Every script sources
  `etc/profile.d/conda.sh` first (auto-located from `$CONDA_EXE`). Don't remove
  that block.
- **logs off `/scratch`**: `#SBATCH --output/--error` point at `$HOME/dyna_logs`
  — writing logs onto Lustre scratch gave intermittent `Errno 116 stale file
  handle` crashes mid-run.
- **each `--steps` is a full epoch** over all 4128 train structures, not a
  minibatch. `--steps 20` = 20 epochs. `--steps 1000` would be infeasible.
- **paper-comparable pose metric is top-4**, not oracle. Our top-4 (~4-5 A on
  CDK2) is ~2x worse than the paper's 2.4 A; oracle (~0.75 A) only shows a
  near-native pose EXISTS among the restarts — the scoring can't select it.
