# DynaFeatureDock

Tests whether Dyna-1 protein flexibility features improve FeatureDock docking
specifically on high-flexibility pockets, where the static crystal structure is
most misleading.

## Hypothesis

FeatureDock's envelope is computed from a static structure. For rigid pockets
(CDK2 with an anchored hinge) the static geometry is reliable. For flexible
pockets (induced-fit sites, mobile loops) the crystal snapshot may not represent
the binding-competent conformation. Dyna-1 identifies residues undergoing µs–ms
motion — exactly the timescale of ligand binding and induced fit. Adding this
signal as an extra token should soften the envelope in dynamic regions and improve
scoring there.

## Architecture change (minimal)

Original FeatureDock input: `(N_voxels, 6 shells × 80 props)` = `(N, 480)`  
→ transformer sees 80 tokens, each a 6-element vector

DynaFeatureDock input: `(N_voxels, 480 + 6)` = `(N, 486)`  
→ transformer sees **81 tokens**: 80 physicochemical + 1 dynamics  
→ dynamics token = mean Dyna-1 flexibility of Cα atoms in each of the 6 shells

The extra token is the same dimensionality (6) as every other token, so it
slots directly into the existing transformer without any architecture hyperparameter
changes. Only `BertModel.forward()` is modified.

## Files

| File | Purpose |
|------|---------|
| `dyna1_predictor.py` | Per-residue flexibility via Dyna-1 or B-factor proxy |
| `augment_features.py` | Appends per-shell dynamics token to `.property.pvar` files |
| `dyna_transformer.py` | Modified transformer (`DynaBertSentClassifier`) |
| `dyna_loaders.py` | Dataset loaders for augmented features + flexibility subsets |
| `flexibility_subset.py` | Assigns pocket-level flexibility scores, partitions dataset |
| `train_dyna.py` | Training loop with early stopping |
| `eval_flexibility.py` | Reports AUC + KL on all / high-flex / low-flex subsets |
| `openadmet_integration.py` | Scores OpenADMET ExpansionRx candidates with the envelope |
| `run_pipeline.sh` | End-to-end shell script |

## Running

```bash
# 1. Compute Dyna-1 flexibility (falls back to B-factors if dyna1 not installed)
#    Install real model: pip install dyna1 fair-esm
python -c "
from dyna_featuredock.dyna1_predictor import batch_flexibility
import pickle
pdbids = open('data/labeled_pdblist.txt').read().split()
flex = batch_flexibility(pdbids, pdb_dir='/data/PDBBind', cache_dir='dyna_featuredock/cache/dyna1')
pickle.dump(flex, open('dyna_featuredock/cache/flexibility_all.pkl','wb'))
"

# 2. Augment FEATURE vectors
python -c "
from dyna_featuredock.augment_features import batch_augment
import pickle
pdbids = open('data/labeled_pdblist.txt').read().split()
flex = pickle.load(open('dyna_featuredock/cache/flexibility_all.pkl','rb'))
batch_augment(pdbids, voxel_dir='/data/voxels', pdb_dir='/data/PDBBind',
              flexibility_dict=flex, out_dir='dyna_featuredock/augmented_pvars')
"

# 3–5. Train + evaluate (see run_pipeline.sh)
bash dyna_featuredock/run_pipeline.sh
```

## Expected results and interpretation

| Scenario | Implication |
|----------|------------|
| Dyna model AUC > baseline on **high-flex** subset | Dynamics signal carries real information about binding-competent geometry |
| Dyna model AUC ≈ baseline on **low-flex** subset | The extra token is not harmful (rigid pockets already well-described) |
| Dyna model AUC ≈ baseline on **both** subsets | Flexibility is second-order; static geometry already dominates |
| Dyna model worse on high-flex | B-factor proxy is noise; retry with real Dyna-1 predictions |

The FeatureDock paper already hints at scenario 3: fine-tuning on kinases gave no
improvement on CDK2, suggesting the general model is a strong baseline. If dynamics
don't help on top of that, the result is still publishable — the null result with
proper ablation is the experiment.

## Reference to Shin-chan OpenADMET approach

The shin-chan team (OpenADMET report) used ensemble models combining physicochemical
and ADMET descriptors. `openadmet_integration.py` adds the DynaFeatureDock envelope
score as a structural feature column for that ensemble, following the same
per-compound scoring logic as FeatureDock's virtual screening mode.
