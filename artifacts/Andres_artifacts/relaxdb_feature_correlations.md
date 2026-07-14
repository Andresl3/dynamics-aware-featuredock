# Real per-residue feature correlations with missing / broadened NMR peaks

**What changed.** The earlier `missing_peak_correlates` figure used a qualitative
strength score synthesized from the paper's text and figures. You asked for a
real number on the x-axis, so I downloaded the Dyna-1 dataset itself
(WaymentSteeleLab/Dyna-1, `RelaxDB_with_other_metrics_30aug2025.json`), built a
per-residue table of **13,525 non-proline residues across 133 proteins**, and
computed **point-biserial r** (which is mathematically Pearson r for a binary
label vs a continuous feature) and **AUROC** for each feature against two targets:
the missing-peak label and the Rex (µs–ms exchange) label.

Files: `relaxdb_feature_correlations.csv` (all numbers), `missing_peak_correlations_real.png`.

## The headline — and it revises my earlier figure

**No single simple structural feature strongly predicts a missing peak.** The
strongest simple correlates are all weak-to-moderate:

| feature | vs missing peak | vs Rex | note |
|---|---|---|---|
| AlphaFold2 pLDDT | r = −0.24 (AUC 0.71*) | r = −0.16 | *AUC<0.5 means *low* pLDDT predicts; inverts to 0.71 |
| MSA coverage | r = −0.22 | r = −0.12 | edges of proteins, poorly covered |
| Loop (vs helix/strand) | r = +0.11 (AUC 0.61) | r = +0.10 | modest |
| Solvent accessibility | r = +0.05 | r = +0.03 | negligible |
| Sequence conservation | r = +0.04 (AUC 0.54) | r = +0.05 | **weak per-residue** |
| R₂/R₁ ratio | — | r = +0.18 (AUC 0.62) | relaxation, Rex only |
| R₂ relaxation rate | — | r = +0.23 (AUC 0.69) | relaxation, Rex only |
| ΔR₂/R₁ (exchange excess) | — | r = +0.30 (AUC 0.93) | near-definitional |

Two honest corrections to the qualitative figure:

1. **Sequence conservation is a weak per-residue predictor (r ≈ 0.04–0.05),** not
   the "strong" bar I drew before. The paper's conservation claim is a real but
   *small distributional shift* (exchange residues are on-average more conserved),
   which is not the same as conservation predicting exchange residue-by-residue.
   My earlier figure overstated it — the real data says so.

2. **pLDDT is NOT a null "myth" — it's actually the single best simple correlate
   here** (r = −0.24; low pLDDT ⇒ more likely missing). I had put pLDDT in the
   "myth" bucket based on the paper's statement that it can't *distinguish µs–ms
   from ps–ns*. That's still true (pLDDT senses disorder of all speeds, so it's
   not *specific* to slow exchange), but as a raw correlate of missing peaks it is
   the strongest of the structural features. Specificity and correlation are
   different claims; the real numbers separate them.

## Why relaxation features only appear for Rex

R₂, R₂/R₁, ΔR₂/R₁ have no values for the missing-peak target — because a residue
with a missing peak has **no measurable R₁/R₂/NOE by definition**. That absence
*is* the signal Dyna-1 exploits; you can't correlate against a number that
doesn't exist. The strong ΔR₂/R₁→Rex correlation (AUC 0.93) is close to
definitional, since Rex is derived from R₂ elevation.

## The real takeaway

This is *why Dyna-1 is a deep model and not a lookup table*: the signal is not in
any single feature (best simple AUROC ≈ 0.71) but in a **nonlinear combination of
sequence + structure context** that the transformer learns. The honest,
non-obvious finding your original question was after is now sharper:

> Every intuitive single-feature predictor — conservation, SASA, loops, even
> B-factor/pLDDT — is individually weak (|r| ≤ 0.24). The predictive power lives
> in the *combination*, which is exactly the gap a learned model fills.

## Method notes
- Labels decoded from `data/vocab.py`: missing = `.`; Rex = {`.`,`^`,`b`}; excluded
  = {`t`,`x`,`p`} (disordered termini / no data / proline).
- point-biserial r via `scipy.stats.pointbiserialr`; AUROC via the Mann–Whitney U
  identity AUC = U/(n₊·n₋).
- All p-values ≪ 0.001 except R₁ vs Rex (p = 0.17) — large n makes even tiny r
  significant, which is exactly why the **effect size (r, AUROC)** is the honest
  axis, not the p-value.
