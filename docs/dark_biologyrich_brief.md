# Dynamics-dark, biology-rich targets — NADSYN1 and ALDH1L2

*Filter this round: proteins with **zero** conformational-change, molecular-dynamics, and
NMR papers, whose disease relevance is nonetheless established by hard wet-lab biology —
human genetics, mouse models, quantitative MS proteomics, transcriptomics, enzymology.
The dynamics are a complete blank; the biology is not. All counts and PMIDs below were
pulled live from PubMed / ChEMBL this session.*

---

## How they were found

I screened ~32 understudied enzymes and dark-kinome proteins, requiring a **hard zero on
all three biophysics axes** (conformational change = 0, MD = 0, NMR = 0). Nine passed.
Of those, I ranked on breadth of *biological* evidence — mouse KO, GWAS/genetics,
proteomics, transcriptomics, enzymology — and two stood out with a genetics-grade or
mouse-grade disease link plus multimodal support.

| Gene | conf | MD | NMR | mouse/KO | GWAS/genetics | proteomics | transcriptomics | enzymology | ChEMBL |
|------|-----:|---:|----:|---------:|--------------:|-----------:|----------------:|-----------:|:------:|
| **NADSYN1** | 0 | 0 | 0 | — | 78 | 7 | 19 | 53 | none |
| **ALDH1L2** | 0 | 0 | 0 | 19 | 6 | 5 | 45 | 41 | none |

Both are **undrugged** (no human ChEMBL target record) and **dynamically unstudied** —
the definition of an open lane.

---

## Candidate 1 — NADSYN1: human Mendelian + GWAS genetics, zero biophysics

**What it is.** NAD synthetase — the final, ATP-dependent step of NAD⁺ biosynthesis
(both de novo and salvage converge here), a glutamine-dependent amidotransferase that
must coordinate an ammonia-tunnel between two active sites. That architecture *implies*
inter-domain motion, but it has never been measured (mechanism query: 0 papers).

**Disease evidence — the strong part.**
- **Human Mendelian.** A homozygous *NADSYN1* variant causes **multiple congenital
  vertebral malformation with neurodevelopmental features** (PMID 42153968) — a direct
  loss-of-function genotype→phenotype link. NAD-deficiency developmental syndromes are an
  established disease class.
- **GWAS.** Osteoporosis-risk GWAS in Korean pre-menopausal women (PMID 40943102);
  vitamin-D-metabolism variants affecting gut microbiota (PMID 42157060); recurrent in
  prenatal structural-anomaly sequencing (PMID 40865752). 78 genetics/variant papers
  total.
- **Enzymology.** 53 papers on the catalytic mechanism / substrate handling — the
  biochemistry is worked out; the *dynamics* of the amidotransferase cycle are not.

**Why dynamics matter here.** A glutamine amidotransferase with an ammonia tunnel is a
machine that has to gate substrate channeling by opening and closing between sites —
exactly the kind of µs–ms motion Dyna-1 is built to flag and CPMG to measure. Disease
variants that don't kill catalysis outright may instead perturb this gating.

---

## Candidate 2 — ALDH1L2: mouse + proteogenomic + redox biology, zero biophysics

**What it is.** Mitochondrial 10-formyltetrahydrofolate dehydrogenase — converts
10-formyl-THF to THF + CO₂, an NADP⁺-dependent enzyme that sits at the drain of
mitochondrial one-carbon metabolism and controls formate / formyl-methionine / ROS
balance. It ties directly into the folate/one-carbon and ferroptosis threads already in
this project.

**Disease evidence — the strong part.**
- **Cancer functional biology (mouse + cell).** ALDH1L2 **suppresses ferroptosis and
  reduces sunitinib sensitivity in renal cancer** (PMID 42304489); regulates **ROS and
  acinar-to-ductal metaplasia in the pancreas** (PMID 41922744, a mouse pancreatic
  phenotype); controls **cancer-cell migration and metastasis** via formate/
  formyl-methionine/ROS (PMID 37245210).
- **Proteogenomics / transcriptomics.** Appears in etiology-based proteogenomic subtyping
  of luminal tumors (PMID 42237381); 45 transcriptomics and 5 proteomics/MS papers.
- **Enzymology + PTM control.** Acetylation of ALDH1L2 tunes redox balance and
  chemosensitivity (PMID 37507016) — 41 enzymology papers, a well-characterized catalytic
  and regulatory picture with **no dynamics**.

**Why dynamics matter here.** ALDH1L2 is a multidomain enzyme (formyl-transfer domain +
aldehyde-dehydrogenase domain linked by a carrier); substrate channeling between domains
is a motion-dependent step. Its function is switched by acetylation — a modification that
often works by shifting a conformational equilibrium, the kind of allosteric motion that
is invisible to crystallography and unmeasured here.

---

## Proposed dynamics experiments (both candidates)

1. **Dyna-1 prediction first.** Run on the apo enzyme; predict where µs–ms exchange
   (missing/broadened HSQC peaks) localizes. Hypothesis: at the **inter-domain / tunnel
   region** that gates substrate channeling, not the isolated active site. This is the
   falsifiable screen — a hit at the channeling interface is the win, a miss is a real
   negative.
2. **¹⁵N CPMG relaxation dispersion** ± substrate (glutamine/ATP for NADSYN1;
   10-formyl-THF/NADP⁺ for ALDH1L2) to map exchange and test **induced fit vs
   conformational selection**: substrate-independent exchange rate ⇒ conformational
   selection; substrate-dependent ⇒ induced fit.
3. **PTM-mimic dynamics (ALDH1L2 specifically).** Compare acetyl-mimic (K→Q) vs wild-type
   by CPMG — if acetylation acts allosterically, the interface exchange population shifts.
   This converts a known biological regulator into a measurable dynamics readout.
4. **Variant dynamics (NADSYN1 specifically).** Compare the disease variant to wild-type —
   if the pathogenic mechanism is gating rather than catalysis, the defect shows up as an
   altered exchange rate, not an altered kcat.

## Why these fit the project
Both are proteins with **decisive disease genetics/mouse biology and complete darkness on
motion** — the cleanest possible case for "the field has the biology but not the
dynamics." A Dyna-1 → NMR program has an unclaimed lane, and each protein's architecture
(amidotransferase tunnel; two-domain formyl-transfer carrier) gives a specific,
testable prediction for *where* the exchange should be.

*Grounding: PubMed counts and PMIDs pulled live this session. NADSYN1 UniProt Q6IA69;
ALDH1L2 UniProt Q3SY69. Neither has a human ChEMBL target record — both undrugged.*
