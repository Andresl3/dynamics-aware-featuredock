# Dynamics-aware FeatureDock — deliverables manifest

Hackathon: **Researcher Track**, July 14–15 2026. Team repo:
`github.com/natesana/dynamics-aware-featuredock` (branch `main`, MIT).

**Thesis:** Two kinases (Abl, Src) that look identical in every crystal structure
bind the same drug (Gleevec) 3,000× differently. The reason is µs–ms motion that
static docking and co-folding models (Boltz-2: 9.5 vs 8.2) cannot see. We give
FeatureDock that missing sense via Dyna-1's flexibility predictions.

All figures are publication-grade (data-fidelity checked, 0 real label overlaps).
No model is trained yet — the Abl/Src result figure is a labeled TEMPLATE, and
every claim rests on published experimental data + transparent rubrics.

---

## Judge-facing documents
| File | What it is |
|------|-----------|
| framing_brief.md | Strategic brief mapped to the four judging axes (Impact 25 / Claude 25 / Depth 20 / Demo 30) |
| project_summary.md | Contest summary — 97-word and 148-word versions (100–200 window) |
| abl_src_experiment.md | Flagship protocol: verified PDBs (1IEP/2OIQ + apo states), ΔScore metric, honest scope |
| REPO_INTEGRATION.md | Where each asset goes in the repo; README hero copy; commit sequence |

## Figures (paper-grade)
| File | Figure |
|------|--------|
| gleevec_paradox.png | **Fig 1** — identical structures, 3,000× gap; Boltz-2 can't separate |
| gleevec_mechanism.png | **Fig 2** — two-step induced-fit free-energy landscape (ΔΔG 4.6 kcal/mol) |
| dynamics_timescale.png | **Fig 3** — the µs–ms timescale gap current methods miss |
| target_impact_landscape.png | Impact × difficulty target landscape, 18 targets, Abl/Src flagged |
| abl_src_result_template.png | Labeled MOCK of the expected flagship win (baseline vs +Dyna-1) |
| flexible_docking_benchmark.png | 18-target Dyna-1 benchmark overview |

## Data (reproducible)
| File | Contents |
|------|----------|
| flexible_docking_benchmark.csv | 18 flexibility-critical targets, apo/holo PDBs, Dyna-1 test tiers |
| target_impact_landscape.csv | Same targets scored: impact & difficulty subscores, UniProt + AlphaFold IDs |
| pdb_verify.csv | RCSB verification log (35/36 live; 1p38→1wfc replacement documented) |

## Video / demo assets
| File | Video beat |
|------|-----------|
| abl_src_01_dynamics_challenge.png | Hook: structure cheap, motion invisible |
| abl_src_02_not_ground_truth.png | Why one crystal misleads |
| abl_src_03_nmr_crash_course.png | How we know motion exists (µs–ms exchange) |
| abl_src_04_missing_peaks.png | The shared static blind spot |
| abl_src_05_dyna1_room.png | Dyna-1 fills the room → our method |

## Key numbers (all from published sources)
- Abl K_D ≈ 80 nM; Src ≈ 240 µM → **3,000×** (Kern 2014, doi:10.1038/nsmb.2891)
- Induced-fit ΔΔG ≈ **4.6 kcal/mol**; reverse rate 0.005 s⁻¹ (Abl) vs 0.3 s⁻¹ (Src)
- FeatureDock tensor: 6×80 → **6×81** with the Dyna-1 channel appended
- Boltz-2 on the pair: **9.5 vs 8.2** (indistinguishable)
- Benchmark: 18 targets across Dyna-1 test tiers A/B/C
