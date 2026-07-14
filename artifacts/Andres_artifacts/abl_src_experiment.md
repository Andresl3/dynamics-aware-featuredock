# Flagship test case — can the Dyna-1 channel discriminate Abl from Src?

**One-line claim under test:** a static-structure docking score cannot separate
Abl from Src for Gleevec (imatinib), but adding the Dyna-1 µs–ms motion channel
opens a score gap that tracks the measured **3,000×** affinity difference.

This is the headline demo experiment. The figure
`abl_src_result_template.png` is a **labeled MOCK** showing the shape of the
expected win; the trained Dynamics-aware FeatureDock fills in the real numbers.

---

## Structures (all verified against RCSB, July 2026)

| Role | Kinase | PDB | Resolution | State / note |
|------|--------|-----|-----------|--------------|
| Primary holo | **Abl** | **1IEP** | 2.1 Å | Abl kinase domain · imatinib (Gleevec) bound |
| Primary holo | **Src** | **2OIQ** | 2.07 Å | chicken c-Src kinase domain · imatinib bound |
| Abl apo / alt | Abl | 1OPJ | 1.75 Å | auto-inhibited c-Abl (conf. selection reference) |
| Abl alt | Abl | 2G1T | 1.8 Å | Src-like inactive conformation of Abl |
| Src apo / alt | Src | 2SRC | 1.5 Å | human c-Src, no imatinib |
| Src alt | Src | 2H8H | 2.2 Å | Src · quinazoline inhibitor |
| Optional | Abl | 3IK3 | 1.9 Å | ponatinib-bound Abl (pan-BCR-ABL) |

Ligand for the discrimination test = **imatinib / STI-571 / Gleevec** on both kinases.

## Ground-truth affinity (Kern 2014, doi:10.1038/nsmb.2891)
- Abl K_D ≈ **80 nM**; Src ≈ **240 µM** → **~3,000×** weaker.
- The gap is **not** in the binding step (both only µM) — it is a slow µs–ms
  induced-fit conformational change *after* binding (ΔΔG ≈ **4.6 kcal/mol**,
  reverse rate 0.005 s⁻¹ Abl vs 0.3 s⁻¹ Src).
- This is exactly the timescale Dyna-1 predicts and static structure / short-MD
  (Boltz-2 training) cannot see.

## Protocol
1. **Featurize** each pocket (existing FeatureDock path): grid points → 6×80 FEATURE tensor.
2. **Baseline arm:** run trained FeatureDock (6×80), score imatinib occupancy on Abl vs Src.
3. **+Dyna-1 arm:** run Dynamics-aware FeatureDock (6×81, Dyna-1 µs–ms channel appended), same scoring.
4. (Optional, augmentation 2) **Ensemble arm:** Protpardelle-1c partial-diffusion
   ensemble per pocket → average the predicted envelope in output space → re-score.
5. **Metric:** ΔScore = score(Abl) − score(Src) for each arm. Success criterion:
   ΔScore(+Dyna-1) ≫ ΔScore(baseline), and the sign/magnitude tracks the 3,000× gap.

## What "success" looks like
- **Baseline:** Abl and Src score distributions overlap (ΔScore ≈ 0) — reproduces
  the Boltz-2 failure mode (9.5 vs 8.2, indistinguishable).
- **+Dyna-1:** Src collapses, Abl holds → a clear separation. That separation *is*
  the finding: motion is the discriminating signal.

## Honest scope
No model is trained yet. The template figure is illustrative. When the model is
trained (see repo `hpc/` SLURM scripts / Colab notebook), replace the mock panels
with real score distributions and report the measured ΔScore per arm.
