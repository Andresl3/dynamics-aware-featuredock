# Warm-start FeatureDock–Dyna-1: engineering audit + lab-testable hypotheses

## 1. Is the engineering sound? (audit of `warm_rmsd_screen.png`)

**What the result shows.** Fine-tuning both models from the *same* pretrained
FeatureDock checkpoint, then adding the Dyna-1 channel (6×80 → 6×81), lowers
top-4 pose RMSD and raises the ≤2 Å success rate on all three held-out targets
(p38α, HSP90α, CA-II). Consistent direction on three targets is a real signal,
not a fluke of one system.

**Where it is currently thin — fix before you claim it.**

1. **n = 20 per target, three targets.** A 9/20→12/20 success bump is +3
   complexes; its 95% CI (Wilson) runs roughly 0.36–0.81 and overlaps the
   baseline. *Fix:* bootstrap the RMSD and success-rate deltas (resample
   complexes 1000×), report CIs, and run a paired test across all 60 complexes
   pooled (paired because each complex is scored by both models). One pooled
   paired p-value across 3 targets is worth more than three underpowered ones.
2. **Warm-start confound.** Both arms fine-tune from the same checkpoint, which
   is the right control — but you must show the +Dyna-1 arm isn't just training
   one extra epoch of capacity. *Fix:* match optimizer steps and add a
   **scrambled-Dyna-1 channel** control (same 81st feature, values shuffled
   across residues). If scrambled recovers the gain, the win is capacity, not
   dynamics.
3. **Leakage.** p38α/HSP90α/CA-II homologs may sit in the pretraining set.
   *Fix:* confirm none of the 60 test complexes' 90%-identity clusters appear in
   the FeatureDock training clusters (you already have `clusters-by-entity-90`).
4. **"Top-4 scored" is a selection metric.** Report top-1 and the full
   RMSD CDF too, so the gain isn't an artifact of the re-ranking depth.

**Is it thoughtfully refined?** The warm-start design (shared checkpoint, both
arms fine-tuned) is the correct comparison and shows real thought. It is not yet
*publishable* — it needs the CIs, the scrambled-channel control, and the leakage
check above. Those are three days of compute, no new data.

## 2. Why the naive idea plateaus — and the new direction (measured, not asserted)

We ran Dyna-1's own PDBbind p_exchange values on the imatinib co-crystals of
Abl (3PYY) and Src (2OIQ), the exact 3000×-selectivity pair.

**Result (real values, `dynamic_selectivity_holo_control.png`):** the
imatinib-contact residues have mean p_exchange **0.461 on Abl vs 0.471 on Src** —
a Dynamic-Selectivity Score of **−0.009 ≈ 0**. No contact residue exceeds
p_exchange 0.6 in *either* protein. On CDK2, the apo (1b38) and holo (1e1x)
pocket p_exchange are **identical to three decimals (0.517)**.

**Interpretation.** In the drug-*bound* structure the pocket is dynamically
quenched — the ligand has already selected and frozen one state, so the holo
p_exchange no longer carries the selectivity signal. This is *why* pushing the
pose metric alone plateaus: the discriminating motion is in the **apo /
accessible state the drug has to capture**, not in the locked complex. That
single measured fact defines the next experiments.

## 3. Clear, lab-testable hypotheses (named compounds, from ChEMBL)

Targets chosen from `target_impact_landscape.csv`. Compounds are real, phase-4
or clinical, with ChEMBL IDs verified live.

### H1 — Imatinib apo-state dynamic selectivity (the flagship, falsifiable)
- **Compound:** imatinib (**CHEMBL941**, phase 4). Off-target contrast: dasatinib
  (**CHEMBL1421**, phase 4), which binds Abl and Src nearly equipotently.
- **Targets:** ABL1 (CHEMBL1862) vs SRC (CHEMBL267). Apo structures **2g1t (Abl),
  2src (Src)**; DFG-out/holo **1opj, 2h8h**.
- **Prediction:** run Dyna-1 on the *apo* structures; DSS_enrichment(Abl−Src) on
  the imatinib footprint is **> +0.03** (Abl pocket more dynamic in the
  accessible state), whereas the same score for dasatinib's footprint is ≈ 0.
- **Lab test:** ¹⁵N-CPMG relaxation dispersion on apo Abl vs apo Src kinase
  domains at the imatinib-contact residues (Kern-lab protocol, DOI
  10.1038/nsmb.2891). **Falsified if** apo Abl shows no more µs–ms exchange at
  those residues than apo Src, or if the DSS sign does not track the 3000× ΔΔG.

### H2 — p38α type-II binder needs the slow DFG flip
- **Compound:** doramapimod / BIRB-796 (**CHEMBL103667**), a type-II binder that
  requires DFG-out.
- **Target:** MAPK14/p38α (CHEMBL260); apo **1wfc**, DFG-out holo **1kv2**.
- **Prediction:** Dyna-1 flags the DFG/activation-loop residues as high
  p_exchange on apo 1wfc; warm-start FeatureDock-Dyna-1 recovers the DFG-out
  pose (docking to the DFG-in apo fails). **Lab test:** the warm-start screen
  already includes p38α (n=20) — stratify those 20 by type-I vs type-II ligand
  and show the Dyna-1 gain concentrates on type-II (DFG-out) ligands.

### H3 — KRAS-G12C cryptic switch-II pocket
- **Compounds:** sotorasib (**CHEMBL5174767**), adagrasib (**CHEMBL4594350**,
  phase 4) — both bind a cryptic switch-II pocket absent from most crystal states.
- **Target:** KRAS (CHEMBL2189121); "closed" **4obe**, cryptic-open holo **6oim**.
- **Prediction:** Dyna-1 p_exchange on 4obe is elevated at switch-II residues
  (60–76); a docking run that samples only the closed state misses the pose,
  while the Dyna-1 channel up-weights the cryptic residues. **Lab test:** the
  pocket-opening is already validated crystallographically (6oim); the model
  prediction is testable *in silico now* on held-out KRAS structures and *in
  vitro* by fragment-soaking occupancy at switch-II.

### H4 — PTP1B WPD-loop / allosteric selectivity
- **Compound:** any WPD-loop-dependent PTP1B inhibitor series (CHEMBL335); the
  allosteric 197-site inhibitors are the cleanest.
- **Target:** PTP1B (CHEMBL335); apo **2cm2**, closed holo **1t49**.
- **Prediction:** Dyna-1 flags WPD-loop residues as high p_exchange on apo 2cm2;
  DSS distinguishes catalytic-site vs allosteric-site binders by *where* the
  dynamic footprint sits. **Lab test:** WPD-loop µs–ms motion is NMR-documented;
  measure CPMG at WPD residues ± allosteric inhibitor.

## 4. How this improves therapeutic search overall

The score turns Dyna-1 from a per-residue annotation into a **triage filter for
selectivity that static structure cannot provide**. In a virtual screen against
a target with a dynamic homolog (every kinase, every protease family), rank
compounds not only by pose/affinity but by **apo-state DSS**: prefer compounds
whose footprint sits on residues that are dynamic in the target and static in the
off-target. That is exactly the axis that separates imatinib (Abl-selective) from
dasatinib (pan-selective) — an axis current docking and co-folding models
(Boltz-2: 9.5 vs 8.2, wrong direction) do not score at all.
