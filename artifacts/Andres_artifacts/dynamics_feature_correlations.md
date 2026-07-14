# Correlations among druggability-relevant dynamics features (real numbers)

You asked for a real correlation — linear or non-linear — on the druggability
dynamics features. Here it is, computed on the Dyna-1 RelaxDB dataset
(133 proteins, ≥85 proteins per pair after dropping missing values), reporting
**both Pearson (linear) and Spearman (monotonic / non-linear)**.

Files: `dynamics_feature_correlations.png`,
`dynamics_feature_correlations_pearson.csv`, `..._spearman.csv`.

## The honest scope, stated plainly
RelaxDB has **no drug-outcome endpoint** — no toxicity, selectivity, cost, or
efficacy column. I verified this (the only protein-level extra field, `lit_tm`,
turns out to be rotational correlation time τc, a molecular-size proxy — it scales
with sequence length, not a melting temperature). So I did **not** invent a
dynamics→outcome correlation. What I *can* correlate honestly is the set of
**measurable per-protein dynamics descriptors that druggability reasoning is built
on** — and those relationships are real and informative.

Descriptor → druggability meaning:
- **µs–ms exchange content** (fraction of residues with Rex) → cryptic / allosteric-pocket propensity
- **missing-peak content** → intermediate-exchange / large-amplitude motion
- **exchange magnitude ΔR₂/R₁** → driver of conformational-state selectivity
- **loop content, conservation, AF2 pLDDT, size τc** → the usual structural intuitions

## Findings

1. **The two cryptic-pocket proxies are strongly coupled but non-linearly:**
   µs–ms exchange content vs missing-peak content is Pearson 0.81 / Spearman 0.64.
   The linear value is inflated by a few very-high-exchange proteins; the rank
   correlation (0.64) is the honest strength. They measure closely related
   physics, as expected.

2. **Loop content is decoupled from slow exchange (r ≈ 0.00–0.03 with everything).**
   This is the non-obvious, useful result: **flexible loops (fast ps–ns motion) do
   NOT mark the µs–ms motions that open cryptic pockets.** You cannot spot a
   cryptic/allosteric site by looking for floppy loops in a structure — the two
   live on different timescales. This directly supports why a dynamics model
   (not a B-factor or loop annotation) is needed for cryptic-pocket discovery.

3. **Exchange magnitude ΔR₂/R₁ anti-correlates with protein size** (Pearson −0.42,
   Spearman −0.31): smaller/faster-tumbling proteins show larger normalized
   exchange excess. The Pearson≫Spearman gap flags this as partly outlier-driven.

4. **Conservation and pLDDT are near-zero with exchange content** (|r| ≤ 0.21),
   consistent with the per-residue result: neither is a strong per-protein marker
   of dynamics either.

## Why show Pearson AND Spearman
Where the two disagree, the disagreement is the message. µs–ms↔missing (0.81 vs
0.64) and size↔ΔR₂/R₁ (−0.42 vs −0.31) are both cases where the **linear
coefficient overstates** a relationship that a few extreme proteins dominate — so
the monotonic (Spearman) number is the more defensible one to quote.

## Method
Pearson via `scipy.stats.pearsonr`, Spearman via `scipy.stats.spearmanr`, on
complete pairs only (≥85 proteins each). Per-protein descriptors are means /
fractions over the 13,525-residue table built from `label`/`DSSP`/feature tracks
in `RelaxDB_with_other_metrics_30aug2025.json` (WaymentSteeleLab/Dyna-1).
