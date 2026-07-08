"""
Dataset loader for Dyna-augmented feature files.

Loads augmented .dyna.pvar files (N, 486) instead of the original .property.pvar (N, 480).
Falls back to the original file if the augmented file is missing (allows mixed datasets).
"""

import os
import pickle
import numpy as np
import torch
from torch.utils.data import TensorDataset


class DynaClassifierDataset(TensorDataset):
    """
    Like ClassifierDataset but loads dyna-augmented features.

    Parameters
    ----------
    datadir      : directory containing both .dyna.pvar and .labels.pkl files
    orig_datadir : directory with original .property.pvar (fallback if no dyna.pvar)
    pids         : list of PDB IDs
    suffix       : label file suffix (default 'HeavyAtomsite')
    resample     : whether to balance classes by resampling
    n_resamples  : number of resampled points per structure
    use_dynamics : if False, load original 480-dim features (ablation mode)
    """

    def __init__(self,
                 datadir,
                 pids,
                 orig_datadir=None,
                 suffix='HeavyAtomsite',
                 resample=True,
                 n_resamples=2000,
                 use_dynamics=True):
        self.datadir = datadir
        self.orig_datadir = orig_datadir or datadir
        self.pids = pids
        self.suffix = suffix
        self.resample = resample
        self.n_resamples = n_resamples
        self.use_dynamics = use_dynamics

    def _load_prop(self, pid):
        if self.use_dynamics:
            dyna_path = os.path.join(self.datadir, f'{pid}.dyna.pvar')
            if os.path.exists(dyna_path):
                with open(dyna_path, 'rb') as f:
                    return pickle.load(f)
        # fallback to original
        orig_path = os.path.join(self.orig_datadir, f'{pid}.property.pvar')
        with open(orig_path, 'rb') as f:
            return pickle.load(f)

    def __getitem__(self, index):
        pid = self.pids[index]
        prop = self._load_prop(pid)                             # (N, 480 or 486)
        labelfile = os.path.join(self.orig_datadir,
                                 f'{pid}.{self.suffix}.labels.pkl')
        with open(labelfile, 'rb') as f:
            labels = pickle.load(f)

        indices = labels[:, 0].astype(int)
        X = prop[indices]
        Y = labels[:, 1]

        if self.resample:
            zeros = np.sum(Y < 0.5)
            ones  = np.sum(Y >= 0.5)
            probs = np.where(Y >= 0.5, 1 / (2 * max(ones, 1)),
                                       1 / (2 * max(zeros, 1)))
            probs /= probs.sum()
            idx = np.random.choice(len(X), size=self.n_resamples,
                                   replace=True, p=probs)
            X, Y = X[idx], Y[idx]

        return torch.from_numpy(X.astype(np.float32)), \
               torch.from_numpy(Y.astype(np.float32))

    def __len__(self):
        return len(self.pids)


class FlexibilitySubsetDataset(DynaClassifierDataset):
    """
    Restricts to the high-flexibility or low-flexibility subset.

    Parameters
    ----------
    flexibility_scores : {pdbid: float}  — mean pocket flexibility per structure
    subset             : 'high' | 'low' | 'all'
    threshold          : quantile cutoff (default 0.75 → top quartile = high-flex)
    """

    def __init__(self, *args, flexibility_scores=None, subset='all',
                 threshold=0.75, **kwargs):
        super().__init__(*args, **kwargs)
        if flexibility_scores and subset != 'all':
            scores = np.array([flexibility_scores.get(p, 0.0) for p in self.pids])
            cutoff = np.quantile(scores, threshold)
            if subset == 'high':
                keep = scores >= cutoff
            else:
                keep = scores < cutoff
            self.pids = [p for p, k in zip(self.pids, keep) if k]
            print(f"[FlexSubset] {subset}-flex subset: "
                  f"{len(self.pids)}/{len(keep)} structures "
                  f"(cutoff={cutoff:.3f})")
