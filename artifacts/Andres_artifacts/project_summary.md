# Dynamics-aware FeatureDock — Project Summary

## 100-word version (contest submission)

Gleevec transformed leukemia treatment by inhibiting the kinase Abl while barely touching its close relative Src — yet Abl and Src are 54% identical and superimpose almost perfectly when Gleevec is bound. Their 3,000-fold affinity difference comes not from shape but from microsecond–millisecond conformational dynamics, which today's docking and co-folding models (even Boltz-2) cannot see. We rebuild the transformer docking model FeatureDock to be dynamics-aware: we inject a per-residue µs–ms motion channel predicted by Dyna-1, add ensemble-averaged and population-weighted scoring, and retrain with CDK2 held out. Claude Science drove the codebase surgery, benchmark curation, and analysis end-to-end.

---

## 150-word version (repo / longer slots)

Gleevec (imatinib) turned a fatal leukemia into a manageable disease by inhibiting the kinase Abl — while barely touching its close relative Src. Yet Abl and Src share 54% sequence identity and, with Gleevec bound, their structures are nearly indistinguishable. The 3,000-fold affinity gap comes not from static shape but from microsecond–millisecond conformational dynamics: Abl clamps the drug in place with a slow induced-fit transition worth ~4.6 kcal/mol that Src cannot. Current docking and co-folding models — including state-of-the-art Boltz-2 — are blind to this timescale and cannot tell the two apart.

We rebuild the transformer docking model **FeatureDock** to be **dynamics-aware**: a per-residue µs–ms motion channel from **Dyna-1** is appended to its pocket featurization (6×80 → 6×81), plus ensemble-averaged envelopes (Protpardelle-1c) and population-weighted multi-state scoring. **Claude Science** performed the codebase surgery, verified every structure against RCSB, curated a flexible-target benchmark, and built the full reproducible Colab pipeline.

---

*Numbers are from Agafonov, Wilson, Otten, Buosi & Kern, "Energetic dissection of Gleevec's selectivity toward human tyrosine kinases," Nat. Struct. Mol. Biol. 2014, 21:848–853 (doi:10.1038/nsmb.2891), and the team's HTC-2026 slide deck.*
