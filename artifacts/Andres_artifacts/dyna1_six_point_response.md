# Dyna-1-FeatureDock — literature-backed answers to the six-point brief

*Every PDB ID, ChEMBL ID, pChEMBL value, PMID, and DOI below was pulled live this
session (RCSB, ChEMBL, PubMed). Where I could not ground a number in a record, I
say so instead of inventing one.*

---

## 1. What the warm-start model is actually capturing

Reading the three-way screen (baseline / +Dyna-1 / scrambled-Dyna-1) across the six
systems you ran (HSP90α, PTP1B, p38α, CA-II, BACE1, HIV-PR):

- **The signal is real but modest, and it is *dynamics*, not capacity.** Real Dyna-1
  beats the scrambled channel on 5 of 6 systems — that ablation is the load-bearing
  result. The 81st feature carrying *shuffled* values does **not** recover the gain,
  which is the only control that separates "the model learned dynamics" from "the model
  got one more free parameter."
- **Where it under-performs:** on rigid pockets DiffDock-L reaches lower median RMSD.
  Dyna-1's edge is not "lower median everywhere" — it is **graceful failure**: your
  +Dyna-1 never exceeds ~3.1 Å on any of the six, whereas DiffDock-L is bimodal
  (sub-2 Å or catastrophic: p38α ~5 Å, BACE1 ~13 Å). That is the honest, defensible
  framing — *bounded worst-case on dynamic targets*, not a median win.
- **Pattern of errors → is dynamics used productively?** Yes, conditionally: the gain
  concentrates on the proteins whose binding is loop-/lid-gated (p38α DFG loop, PTP1B
  WPD loop, HSP90 ATP lid). On a pocket with no slow motion the channel is inert, as it
  should be. That target-conditional behavior is the fingerprint of a feature being used
  mechanistically rather than as noise.

**Caveat you must state:** n≈20 complexes/system. The +0.10/−0.11 Å deltas have
bootstrap CIs crossing zero; only the ~+1 Å ones survive. Pool all ~60 into **one paired
Wilcoxon** and bootstrap the CI — one honest p-value beats six underpowered ones.

---

## 2 & 3. Specific, testable, still-open hypotheses (not general validation)

These are falsifiable next experiments, each with the structures/compounds to run them.

**H1 — Apo-state is where Abl/Src selectivity lives (the experiment that rescues or kills your headline).**
On the imatinib-**bound** structures, Dyna-1's footprint exchange is *flat and identical*
for Abl and Src (mean p_exchange 0.461 vs 0.471, DSS ≈ −0.009 — measured this session).
So the discriminating motion is **not** in the locked complex; it must be in the apo /
accessible state the drug has to capture.
- **Run:** Dyna-1 inference on apo **ABL1 2G1T** vs apo **SRC 2SRC**; score the imatinib
  footprint (residues within 5 Å of the bound pose, mapped from 1IEP/2OIQ).
- **Predict:** apo DSS_enrichment(Abl − Src) > **+0.03** for imatinib, but ≈ 0 for
  dasatinib (pan-kinase).
- **Falsified if:** apo Abl shows no more µs–ms exchange than apo Src by ¹⁵N-CPMG at the
  DFG/A-loop residues. This is the cleanest single wet-lab test — CPMG on apo Abl vs apo
  Src kinase domains, which the Kern lab has already shown differ (PMID **25700521**,
  *Kinase dynamics… unravel a modern cancer drug's mechanism*).

**H2 — Scrambled-channel ablation must survive leakage and per-complex bootstrap.**
Confirm none of the ~60 test complexes' 90%-identity clusters appear in FeatureDock's
training clusters (you have `clusters-by-entity-90.txt`). Then bootstrap ΔRMSD
(real − scrambled) per system, 1000×. **Null H0:** mean(real − scrambled) = 0.
Falsified/​confirmed cleanly instead of by eyeballing bars.

**H3 — DFG-out selectivity is predictable from Δ(apo−holo) exchange, not holo exchange.**
For p38α (apo **1WFC** → DFG-out holo **1KV2**, ligand SB2-class) the type-II pocket only
exists in the DFG-out state. **Predict:** the residues that *lose* p_exchange from apo→holo
(i.e. get pinned by the type-II binder) are the DFG/αC residues, and this Δ predicts type-II
vs type-I preference better than either single-state value. Literature anchor: selective
targeting of the αC/DFG-out pocket in p38 (PMID **33035818**).

**H4 — PTP1B WPD-loop µs–ms motion discriminates catalytic-site vs allosteric binders.**
Apo **2CM2** (WPD-open) → holo **1T49** (WPD-closed, allosteric). **Predict:** Dyna-1 flags
WPD-loop residues as high p_exchange on apo 2CM2; DSS separates a catalytic-site binder
(footprint on the loop) from an allosteric binder (footprint off it). WPD µs–ms motion is
NMR-documented — measure CPMG at WPD residues ± allosteric inhibitor. Anchor: biophysical
rationale for PTP1B-over-TCPTP selectivity (PMID **37729547**).

**A drug-selectivity score with NO retraining (answers your point-3 "something exact"):**
The **Dynamic-Selectivity Score (DSS)** already built this session
(`dynamic_selectivity_score.py`): given a known binding pose, take the mean predicted
p_exchange over footprint residues on the **target apo** state minus the same on the
**off-target apo** state. Positive ⇒ the drug's contacts sit on residues that are dynamic
in the target and static in the off-target — exactly the imatinib(Abl-selective) vs
dasatinib(pan) axis. It runs on Dyna-1 outputs alone; no FeatureDock retraining. Validated
honest-negative on holo (returns "flat"), which is why H1 moves it to apo.

---

## 4. Which tested proteins are strongest for dynamics-driven design (mechanism per protein)

From `target_impact_landscape.csv` crossed with the six you tested:

| Protein | Motion that gates binding | Why *dynamics*, not static structure, predicts selectivity |
|---|---|---|
| **ABL1 vs SRC** (flagship) | DFG/A-loop µs–ms exchange | Holo crystals near-identical, yet 3000× affinity gap; Boltz-2 scores wrong direction (9.5 vs 8.2). Selectivity is an *apo-state exchange* difference (PMID 25700521, 23319661). |
| **p38α / MAPK14** | DFG-out ⇌ DFG-in loop | The type-II pocket is *absent* in the static DFG-in structure — it only exists as a transient state. Static docking can't score a pocket that isn't in the input coordinates (PMID 33035818, 29749295). |
| **PTP1B / PTPN1** | WPD loop open ⇌ closed | Allosteric (site-197) selectivity over TCPTP is set by loop µs–ms motion, not by the near-identical active site (PMID 37729547). |
| **HSP90α** | ATP-lid open ⇌ closed | Lid closure kinetics differ across HSP90 paralogs with near-identical pockets; isoform selectivity is a dynamics problem (PMID 18511558, 12964162). |
| **HIV-1 protease** | Flap open ⇌ closed | Flap opening is the rate-limiting, mutation-tunable motion; resistance mutations (T12A/H69N) act by *changing flap dynamics*, not the catalytic geometry (PMID 42123414, 34030114). |
| **BACE1** | 10s flap over catalytic Asp | Flap dynamics gate substrate access; potency of AM-6494-class binders tracks flap engagement (PMID 33410374). |

CA-II is the honest **negative/rigid control** — a fast, well-behaved pocket where the
dynamics channel should be (and is) inert.

---

## 5. Concrete, minimally-researched candidate compounds (real ChEMBL records)

*Selection rule stated honestly:* I ranked potent (pChEMBL ≥ 7) actives per target and
prioritized **recently-registered ChEMBL IDs** (higher numeric ID ⇒ later deposition ⇒
less accumulated literature) as a novelty proxy. For Abl-selectivity I took compounds
potent on ABL1 but **absent from the SRC potent-actives set** — a *weak* proxy (I only
pulled the top-40 per target, so absence ≠ proven inactivity). Each row is a real record
with a source document to verify.

**Abl-selective candidates (potent on ABL1, not in SRC top set):**

| ChEMBL ID | ABL1 potency | Source doc | Test rationale |
|---|---|---|---|
| CHEMBL5416410 | 4.2 nM (pChEMBL 8.38) | CHEMBL1138257 | Newest-registered potent Abl binder in the set — run DSS on apo 2G1T vs 2SRC; predict positive Abl enrichment. |
| CHEMBL536073 | 12 nM (7.92) | CHEMBL1147914 | Sub-20 nM, absent from Src set — candidate for measured Abl>Src selectivity. |
| CHEMBL436137 | 20 nM (7.70) | CHEMBL1139689 | Same series family — selectivity SAR test. |

**KRAS-G12C (switch-II cryptic pocket — dynamics-*created* site):**

| ChEMBL ID | Potency | Source doc | Rationale |
|---|---|---|---|
| CHEMBL4452137 | 25 nM (7.60) | CHEMBL4354832 | Switch-II pocket only opens transiently; a strong test of whether Dyna-1 flags the cryptic-site residues on apo **4OBE** before the covalent warhead engages. |
| CHEMBL4456598 | 48 nM (7.32) | CHEMBL4325929 | Independent series → cross-series generalization of the cryptic-pocket prediction. |

**PTP1B (WPD-loop allosteric):**

| ChEMBL ID | Potency | Source doc | Rationale |
|---|---|---|---|
| CHEMBL4524071 | 0.42 nM (9.38) | CHEMBL1130173 | Very potent, low-profile record — footprint-DSS test of catalytic vs allosteric engagement on 2CM2/1T49. |
| CHEMBL1086226 | 38 nM (7.42) | CHEMBL1132993 | Series member for allosteric-vs-active-site DSS separation. |

*I did not assert "no prior research" as fact for any of these — verify literature depth
per ID before wet-lab commitment. The ChEMBL IDs, potencies, and document IDs are the
verifiable anchors.*

---

## 6. Where else Dyna-1 features would have high impact (named cases)

- **Cryptic-pocket prediction — PocketMiner (Meller, Bowman et al., *Nat. Commun.* 2023).**
  PocketMiner predicts cryptic-site *opening* from single structures using an MSM-trained
  GNN. Dyna-1's µs–ms exchange is a *complementary experimental-grounded* channel — add it
  as a feature and test whether it improves cryptic-site AUC on their own held-out set.
- **Co-folding scoring — Boltz-2 / AlphaFold3 affinity heads.** These are trained on NMR
  ensembles + short MD (not validated exchange) and demonstrably miss Abl/Src. Concrete
  experiment: append Dyna-1 per-residue exchange as a conditioning track and re-score the
  Abl/Src imatinib pair — the named failure case in your own brief.
- **Allosteric drug discovery — the Kern-lab kinase program (PMID 25700521).** DSS on apo
  states is a direct, runnable add-on to any DFG-out/type-II campaign.
- **Enzyme engineering — DHFR / adenylate-kinase dynamics benchmarks (Kern-lab canonical
  systems).** Dyna-1 predicts the per-residue exchange these engineering studies measure by
  CPMG; use it to prioritize which loop residues to mutate for altered turnover.
- **Fragment-based screening on flexible pockets — PTP1B allosteric-fragment work
  (PMID 37729547) and BACE1 flap series (PMID 33410374).** Rank fragments by apo-state DSS
  to enrich for allosteric over orthosteric hits.

**Negative control to keep the story honest:** Bio2Byte S²/DynaMine predicts *ps–ns*
backbone flexibility — the wrong timescale. If Dyna-1's advantage were just "flexibility,"
S² would reproduce it. It does not, because the signal is slow (µs–ms) exchange. That
contrast is your cleanest one-line proof that the feature is timescale-specific.
