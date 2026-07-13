# Scouting a dynamics-blind therapeutic target — a Kern-style read of the literature

*Premise: find a protein whose **function is a conformational switch**, that has deep
disease / pathway / interaction literature, yet whose µs–ms dynamics have never been
measured — the exact blind spot where a Dyna-1 + relaxation-dispersion program has room
to say something new. All counts below were pulled live from PubMed / ChEMBL this
session, not recalled.*

---

## How the field was scanned

I scored ~40 metabolic and moonlighting enzymes by a "Kern gap":
`(disease + pathway + 2·RNA-interaction papers) / (dynamics papers + 1)`. The raw top
(GLS, NAMPT) are already saturated drug programs, so volume alone is the wrong filter.
I re-ranked on the sharper criterion — **the catalytic cycle IS a large conformational
change, the dynamics are unmeasured, and the chemical matter is thin** — which surfaces
two candidates that a biophysicist reading for "promising but mechanistically dark"
would stop on.

| Gene | All papers | Conformational-change papers | MD | NMR Rex | ChEMBL potent inhibitors |
|------|-----------:|-----------------------------:|---:|--------:|-------------------------:|
| **SHMT2** (mito) | 397 | 3 | 3 | **0** | 6 (best 437 nM) |
| **ACO1 / IRP1** | 781 | 15 | 1 | **0** | **0 — no ChEMBL target record** |

Neither protein has a single NMR relaxation-dispersion study. That is the opening.

---

## Candidate 1 — ACO1 / IRP1: the enzyme that becomes an RNA switch by moving a whole domain

**Why it is a switch.** ACO1 is bifunctional. With its [4Fe-4S] cluster assembled it is
cytosolic **aconitase**; when iron is scarce the cluster disassembles and the protein
becomes **Iron Regulatory Protein 1 (IRP1)**, which clamps onto iron-responsive element
(IRE) stem-loops in the mRNAs of ferritin, transferrin receptor, HIF2α and others. The
two functions are mutually exclusive and the interconversion requires a **large hinge
opening between domains 3 and 4** to expose the RNA-binding cleft — a textbook
conformational switch that gates which of two biologies the cell runs.

**Why it matters therapeutically.** IRP1 sits upstream of HIF2α translation; targeting
HIF2α translation with the IRP1-activating drug Tempol was shown to suppress
VHL-deficient clear-cell renal carcinoma (PMID 23178531). It is also the hinge of the
iron / ferroptosis axis now central to oncology (ferritinophagy, NFS1/Fe-S supply —
PMIDs 41692973, 41594574). Modulating the aconitase↔IRP1 equilibrium is a way to tune
iron handling and ferroptosis sensitivity — but there is **no chemical probe program**
(zero ChEMBL target record), because nobody knows whether the switch is druggable.

**The dynamics gap.** 781 papers, 15 touching the open/closed crystallography, exactly
**one** MD study, **zero** solution dynamics. The rate and mechanism of the
holo→apo domain opening — the step that actually decides enzyme-vs-regulator — has never
been measured.

**Is binding induced fit or conformational selection?** This is the falsifiable question.
- *Conformational selection* predicts the apo/cluster-free protein already samples the
  open, RNA-competent state transiently in the µs–ms window; IRE binding shifts a
  pre-existing equilibrium. Signature: CPMG relaxation dispersion on apo-IRP1 shows
  exchange at the hinge residues **before** RNA is added, with a rate independent of
  [IRE].
- *Induced fit* predicts the open state is populated only after IRE contacts form.
  Signature: hinge exchange appears/accelerates only in the presence of sub-saturating
  IRE, with a [IRE]-dependent rate.

---

## Candidate 2 — SHMT2: catalysis gated by an oligomeric-state switch, plus a moonlighting job

**Why it is a switch.** SHMT2 is the mitochondrial serine hydroxymethyltransferase of
one-carbon metabolism. Its activity is controlled by a **PLP-dependent dimer↔tetramer
equilibrium**: the tetramer is the catalytically competent species, and the dimer is the
form that moonlights as a structural subunit of the **BRISC deubiquitinase complex**,
coupling one-carbon flux to inflammatory signalling. So the same population shift that
turns catalysis on also releases the moonlighting partner — one conformational/assembly
switch, two cellular outputs.

**Why it matters therapeutically.** SHMT2 is a recurrent cancer-metabolism dependency;
this session's search returned 43 therapeutic papers including a **breast-cancer
metabolic-immune subtype defined by G6PD + SHMT2** (PMID 41819344), covalent
SHMT2 inhibition driving ferroptosis (PMID 42378651), and roles in pulmonary vascular
remodelling and TGF-β fibrosis. It connects directly to the breast-cancer / T-cell
one-carbon threads already in this project.

**The dynamics gap.** 397 papers, only 3 on conformational change, 3 MD, **zero** NMR
relaxation dispersion. The existing chemistry (6 potent binders, best ~437 nM) targets
the PLP active site; the **allosteric dimer↔tetramer interface** — the switch that
actually gates both functions — has never been probed dynamically and has no reported
allosteric ligand.

**Is binding induced fit or conformational selection?** The interesting drug hypothesis
is an *interface* modulator, not another active-site inhibitor:
- *Conformational selection*: the dimer transiently samples the tetramer-competent
  interface geometry; an allosteric ligand that recognizes that transient state would
  shift the population toward (or away from) the active tetramer. Signature: CPMG on the
  dimer shows exchange localized to interface residues, ligand-independent in rate.
- *Induced fit*: the competent interface forms only upon partner (second dimer, or PLP)
  binding. Signature: interface exchange is contingent on partner concentration.

---

## Proposed dynamics experiments (same protocol for both, Kern-style)

1. **¹⁵N CPMG relaxation dispersion** on the two functional states (ACO1: apo vs holo;
   SHMT2: dimer vs tetramer, controlled by concentration / PLP). Map per-residue R_ex
   to locate the µs–ms exchange — predict it concentrates at the hinge (ACO1) /
   oligomer interface (SHMT2), *not* the active site.
2. **CEST / R1ρ** to catch slower (ms) minor states and extract the excited-state
   population and exchange rate k_ex.
3. **Ligand / partner titration** to distinguish the two binding mechanisms by the rules
   above: [ligand]-independent exchange rate ⇒ conformational selection; [ligand]-
   dependent ⇒ induced fit.
4. **Dyna-1 prediction first, as the falsifiable screen.** Run Dyna-1 on both states
   and predict *where* missing/broadened peaks (µs–ms exchange) should appear before
   collecting NMR. A hit at the switch residues is the win; a miss is a real negative.
   This is exactly the protein-level-triage use of Dyna-1 established earlier in the
   project — flag the dynamic region, then measure it.

## Why these two fit the project's thesis
Both are proteins where **static structure is uninformative about function** — the
crystal shows one state, but the therapeutically relevant behaviour is the *rate and
population* of the switch between states. That is the same gap Abl/Src exposed for
docking, generalized to target discovery: the dynamics, not the fold, carry the signal,
and Dyna-1 is the cheap way to point NMR at the right residues.

*Grounding: PubMed counts and PMIDs, ChEMBL target/bioactivity records pulled live this
session. ACO1/IRP1 UniProt P21399; SHMT2 UniProt P34897 (ChEMBL mito target
CHEMBL4295747, cytosolic SHMT1 CHEMBL1772927).*
