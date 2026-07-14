# Correlating Dyna-1 per-residue predictions against ground truth

*A map of datasets you can align, per residue, to a Dyna-1 flexibility/exchange prediction —*
*organized by the one thing that matters: does the observable report on the same timescale*
*Dyna-1 predicts?*

---

## The governing principle: match the timescale

Dyna-1 predicts **per-residue µs–ms conformational exchange** — essentially, which residues
would show NMR relaxation dispersion (Rex). "Dynamics" datasets span 12 orders of magnitude
in time, and most report on the *wrong* window:

- **ps–ns** (fast librations): NMR S² order parameters, vanilla MD RMSF. A residue can be
  rigid on ps–ns but exchange on µs–ms, or vice-versa. Correlating Dyna-1 against these
  measures a **different phenomenon** and will understate its accuracy.
- **µs–ms** (the target): CPMG / R1ρ relaxation dispersion, CEST. **This is the match.**
- **ms–s and slower** (folding, HDX): protection factors convolve dynamics with
  thermodynamic stability — related but not the same variable.

So: validate primarily against µs–ms observables, and use fast-timescale data (S²) as a
**negative control** — a good Dyna-1 predicts exchange that S² does *not* already explain.

---

## Tier 1 — direct matches (µs–ms exchange, per residue)

1. **The Dyna-1 paper's own curated dataset** (Wayment-Steele, El Nesr et al. 2025).
   Same target variable, already residue-labeled. Use their held-out split so you correlate
   on residues the model never trained on. This is your first and cleanest check.
2. **BMRB** (bmrb.io) — the primary NMR repository, with a REST API and FTP. Contains
   R1/R2/hetNOE, and where deposited, **CPMG relaxation dispersion, R1ρ, and CEST**. The
   dispersion data is sparse and heterogeneously formatted (you harvest per-entry, it is not
   pre-tabulated), but it is the largest source of real per-residue exchange measurements.
3. **The canonical Kern-lab systems** — Cyclophilin A, Adenylate kinase, PTP1B, DHFR,
   RNase A, and Abl/Src — where CPMG *and* long MD *and* solved ensembles all exist in the
   literature. Small n, but the gold standard, and **already the Tier-A systems in this
   project's flexible-docking benchmark**. Best place to show a tight, defensible correlation.

## Tier 2 — MD ensembles (indirect; fast unless you extract slow modes)

4. **ATLAS** (dsimb.inserm.fr/ATLAS) — standardized all-atom MD (3×100 ns) for ~1500 PDB
   proteins, with per-residue RMSF/flexibility ready to download. Huge coverage, but RMSF is
   dominated by fast motion — a flexibility baseline, not a µs–ms proxy.
5. **mdCATH** (HuggingFace) — MD across CATH domains; good for building your own slow-mode
   metrics (tICA / Markov-state timescales) rather than raw RMSF.
6. **DE Shaw / Anton ultra-long trajectories** (BPTI to 1 ms; the fast-folder set,
   Lindorff-Larsen 2011) — the only MD that actually reaches ms. Available on request.
   Extract µs–ms modes via MSM/tICA; do **not** correlate against raw RMSF.

## Tier 3 — conformational heterogeneity / state pairs (locates motion, no timescale)

7. **PED — Protein Ensemble Database** (proteinensemble.org, REST API) — experimental
   ensembles (SAXS/NMR); strongest for disordered/flexible regions.
8. **CoDNaS** — RMSD between alternative solved states of the same protein; a per-residue
   "where does it move between states" signal.
9. **qFit multiconformer models + B-factors / ensemble refinement** (RCSB) — weakest
   proxy; B-factors are confounded by lattice, resolution, and refinement. Alt-conformers
   are a better hint than raw B.

## Tier 4 — adjacent phenomena (cross-checks, not the same variable)

10. **PocketMiner** (Meller & Bowman 2023) — cryptic-pocket-formation labels from MD;
    cryptic sites overlap mobile regions, so a useful spatial cross-check.
11. **Start2Fold** — HDX protection factors + Φ-values; slower (folding) timescale.
12. **Bio2Byte S² compilations** (DynaMine training data) — Lipari-Szabo S², ps–ns.
    **Use as the negative control.**

---

## How to actually run the per-residue correlation

**1. Align numbering first.** Map both the prediction and the ground truth onto a common
index — UniProt residue number is safest; author/PDB numbering has gaps and insertion
codes. Drop residues missing in either. Keep chain identity explicit. This step causes
most spurious "no correlation" results.

**2. Pick the metric by the ground-truth type.**
- Binary label ("residue shows significant Rex"): **ROC-AUC and PR-AUC** — Dyna-1 outputs a
  per-residue probability, so this is the natural scoring. PR-AUC matters because exchanging
  residues are a minority class.
- Continuous magnitude (ΔR2eff, kex, Rex, or an MD slow-mode amplitude): **Spearman ρ**
  (rank correlation — robust to the nonlinear relationship between score and rate).

**3. Match the state.** Exchange is state-dependent — apo vs holo, active vs inactive, ±
mutation (this is exactly the Kim-et-al. mutation-rewiring point). Predict on the same
structural state the measurement was made on, or you'll blame the model for a state
mismatch.

**4. Control for the trivial predictor.** Show Dyna-1 beats (a) S² / fast RMSF and
(b) raw B-factor / solvent exposure. If it only recovers what B-factors already tell you,
it isn't adding the µs–ms information that is the whole point.

**5. Report per-protein, not just pooled.** A pooled correlation across proteins can be
inflated by between-protein differences. Report the distribution of per-protein AUCs/ρ.

---

## Reachability note

BMRB, PED, and ATLAS expose public APIs but sit outside this sandbox's default science
allowlist (which covers NCBI, UniProt, RCSB, EBI, Ensembl, etc.). If you want me to pull
any of them here, I can request access to the specific domain and build the harness against
live data — otherwise the cleanest starting point needs no external fetch at all: the
Dyna-1 paper's own labeled set plus the Kern Tier-A systems already in the benchmark.

---

*Companion file: `dyna1_validation_datasets.csv` — the same table, filterable by timescale
and match quality.*
