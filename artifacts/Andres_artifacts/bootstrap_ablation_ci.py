"""
bootstrap_ablation_ci.py
-------------------------
Paired bootstrap 95% CIs for the Dyna-1 ablation panel (scrambled - real).

You already have, per system, the per-complex top-4 pose RMSD arrays from the
warm-start screen. This computes an honest CI on the *paired* difference
delta_i = RMSD_scrambled(i) - RMSD_dyna(i), resampling complexes with
replacement. Paired is correct: scrambled and real Dyna-1 are evaluated on the
SAME complexes, so the shared per-complex difficulty cancels and the CI is
tighter (and more defensible) than an unpaired one.

Drop your real arrays into RMSD_DYNA / RMSD_SCRAM below (each a length-20 list
per system, complex order matched) and run. It prints the (lo, hi) whisker
numbers and a ready-to-paste dict for the figure.
"""
import numpy as np

# ---- REPLACE THESE with your real per-complex arrays (order matched) ---------
# key -> (real_dyna_rmsds, scrambled_rmsds), each length = n complexes for that system
DATA = {
    # "HSP90a": ([...20 values...], [...20 values...]),
    # "PTP1B":  ([...], [...]),
    # ...
}
# -----------------------------------------------------------------------------

N_BOOT = 10000
SEED = 42

def paired_delta_ci(dyna, scram, n_boot=N_BOOT, seed=SEED, alpha=0.05):
    dyna = np.asarray(dyna, float); scram = np.asarray(scram, float)
    assert dyna.shape == scram.shape, "arrays must be paired / same length"
    delta = scram - dyna                      # positive => real beats scrambled
    n = len(delta)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot = delta[idx].mean(axis=1)
    lo, hi = np.percentile(boot, [100*alpha/2, 100*(1-alpha/2)])
    # two-sided bootstrap p for H0: mean delta = 0
    p = 2 * min((boot <= 0).mean(), (boot >= 0).mean())
    return dict(mean=float(delta.mean()), lo=float(lo), hi=float(hi),
                p=float(p), n=n, significant=bool(lo > 0 or hi < 0))

if __name__ == "__main__":
    out = {}
    for k, (dyna, scram) in DATA.items():
        r = paired_delta_ci(dyna, scram)
        out[k] = (round(r["lo"], 3), round(r["hi"], 3))
        star = "*" if r["significant"] else " "
        print(f"{k:8s} delta={r['mean']:+.3f}  95%CI[{r['lo']:+.3f},{r['hi']:+.3f}]  p={r['p']:.3f} {star}")
    print("\n# paste into figure as CI = {system: (lo, hi)}")
    print("CI =", out)
