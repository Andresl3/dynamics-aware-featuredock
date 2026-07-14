# Dynamics-aware FeatureDock — Framing Brief for the Judges

*How to position this project to win. Read this once before writing the demo video script or the repo landing page.*

---

## The one sentence

> **Two proteins that look identical in every crystal structure bind the same blockbuster drug 3,000× differently — and the reason is motion no current docking or co-folding model can see. We teach a docking model to see it.**

That sentence is the whole project. Everything below is in service of making a judge believe it and want to build on it.

---

## Why this wins on each judging axis

The rubric is **Impact 25 / Claude Use 25 / Depth & Execution 20 / Demo 30**. Demo + Impact = 55% of the score, so the Abl/Src story and a compelling walk-through matter more than any single metric.

### Impact (25%) — "a finding others can build on"
- **The finding is a *dimension*, not a data point.** Structure-based drug design has ridden one wave — AlphaFold2 made *static* structure cheap and universal. The next bottleneck is that static structure is provably insufficient for selectivity: Gleevec is the textbook proof. The project argues (and builds the tooling to test) that **µs–ms conformational dynamics is the missing input feature** for the next generation of docking models.
- **Concrete, quantified stakes.** Kinase selectivity is a multi-billion-dollar clinical problem — off-target kinase inhibition drives toxicity and failed trials. A docking model that ranks selectivity by dynamics rather than shape is directly useful to any group screening kinase (or other flexible-target) libraries.
- **Reproducible and open.** Every input is public and scriptable: PDBBind (structures), Dyna-1 (motion), ChEMBL (potency), RCSB (Abl/Src). The repo is MIT-licensed and the pipeline runs end-to-end on free Colab.

### Claude Use (25%) — "creative, beyond a basic application"
Document the workflow explicitly in the demo — judges reward *seeing* Claude Science do research-grade work:
- Read and cross-referenced 3 preprints + the FeatureDock paper + supplement, and **pulled the actual train/val split code out of the GitHub repo** to confirm exactly where the Dyna-1 channel must be injected (6×80 → 6×81) and how the CDK2 hold-out is built.
- **Verified every PDB ID against the live RCSB API** while curating the flexible-target benchmark — caught and replaced a dead accession (`1p38` → `1wfc`) so nothing fabricated entered the dataset.
- Turned the Kern 2014 energetics paper into publication-grade explanatory figures with the exact microscopic rate constants.
- Built a target-impact/difficulty landscape metric from literature + UniProt/AlphaFold to point at the *next* Abl/Src-like opportunities.
- **Talking point that surprises:** "Claude Science didn't just summarize the papers — it opened the codebase, found the 2-line split logic, and told us which tensor dimension to widen."

### Depth & Execution (20%) — "pushed past the first idea, real craft"
- The first idea was "add a dynamics channel." The project pushed to **three** distinct, mechanistically-motivated augmentations at three different points in the pipeline (input featurization ①, output-space ensemble averaging ②, downstream population-weighted scoring ③), and correctly reasons about which require retraining.
- The code path is **already validated locally** — `featurize_dyna1_channel.py` takes the shipped CDK2 example (`1b38`, 3,163 grid points) from `(3163,480) → (3163,486)`, all 290 residues mapped, and both the 80- and 81-wide classifiers run forward+backward cleanly. That is real engineering, not a slide.
- **Honesty as craft:** the repo already labels its result plots as hypothetical. Keep that. Judges trust a team that says "here is the shape of result we designed the experiment to test, and here is the code that will produce it" far more than one showing suspiciously clean numbers.

### Demo (30%) — "working, compelling, cool to watch"
The demo is the highest-weighted axis. Structure it as a **detective story**, not a software tour (shot list below). The emotional beat: *show two structures the viewer literally cannot tell apart, reveal the 3,000× number, watch the SOTA model (Boltz-2) fail, then reveal that the answer was motion all along.*

---

## The scope line — say this out loud, don't hide it

**What is done:** the scientific case, the three-augmentation design, the validated Dyna-1-channel code path, the CDK2-validation split, the flexible-target benchmark, and the full Colab training pipeline.

**What is pending:** the actual retrain + the real Abl/Src potency numbers (needs GPU + a registered PDBBind download). The Abl/Src result figure is a **labeled template** showing the expected shape of the win; the trained model fills in the real bars.

Stating this cleanly is a *strength* — it makes the project reproducible ("here's exactly what to run") and honest. Judges reward "a discrete, reproducible analysis others can build on" — that is precisely a validated pipeline + a designed benchmark + a sharp hypothesis.

---

## The 3-minute demo video — shot list

| Time | Shot | Line |
|------|------|------|
| 0:00–0:25 | Two kinase structures side by side, Gleevec bound, slowly rotating — **visually identical**. | "This is Abl. This is Src. 54% identical, and with Gleevec bound their structures superimpose almost perfectly. One is the target of a drug that turned a fatal leukemia into a managed condition. The other barely binds it — 3,000 times weaker. Nothing in these structures tells you which is which." |
| 0:25–0:50 | Boltz-2 output: two nearly-equal scores (9.5 vs 8.2). | "We asked Boltz-2 — state-of-the-art co-folding — to tell them apart. It can't. Because it, like almost every docking model, was trained on static structures and short-timescale motion. The answer lives on a timescale it never sees." |
| 0:50–1:30 | Kern free-energy landscape animation: E + I → E.I → E*.I; Abl's well drops to nanomolar. | "The 2014 Kern lab work solved it: Gleevec binds *both* kinases weakly at first. Then Abl does something Src barely does — it clamps down with a slow, microsecond-to-millisecond conformational change worth 4.6 kcal/mol. Selectivity isn't in the shape. It's in the motion." |
| 1:30–2:15 | Claude Science screen recording: reading the FeatureDock repo, finding the split code, the 6×80→6×81 channel diagram, the local validation output. | "So we used Claude Science to rebuild FeatureDock as a *dynamics-aware* docking model. It read the codebase, found exactly where to inject a per-residue µs–ms motion channel from Dyna-1, and validated the code path on CDK2 — 3,163 grid points, all 290 residues mapped." |
| 2:15–2:45 | The target-impact landscape scatter; flagship targets lighting up. | "And this isn't just Abl. We built a map of the highest-impact, hardest-to-drug targets whose selectivity is governed by dynamics — the next Gleevec stories waiting to be told." |
| 2:45–3:00 | Repo landing page + the honest banner. | "Everything's open, reproducible, and runs on free Colab. This is the missing dimension for the next generation of drug design." |

---

## Words to use / words to avoid

**Use:** "missing dimension," "selectivity by dynamics," "the timescale current models can't see," "reproducible pipeline," "AlphaFold made structure cheap; dynamics is next."

**Avoid:** claiming the model already beats anything (it isn't trained yet); "solved drug design"; any real-looking Abl/Src bar chart without the SYNTHETIC/TEMPLATE label. One unlabeled fake number, spotted by a judge, costs you the whole Depth axis.
