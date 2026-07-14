# What correlates with missing / broadened peaks in NMR HSQC spectra

**Source of truth:** Wayment-Steele, El Nesr, Kern et al., *"Learning millisecond
protein dynamics from what is missing in NMR spectra"* (bioRxiv 2025.03.19.642801v3) —
the Dyna-1 paper. Its observable **is** the missing/broadened peak, so its own
analysis is the authoritative catalog of what does and doesn't correlate.
Companion files: `missing_peak_correlates.csv` (21 features scored) and
`missing_peak_correlates.png` (grouped diverging chart).

## The one physical fact everything hangs on

A backbone amide peak goes missing or broadens beyond detection when the residue
interconverts between chemical environments at a rate **kₑₓ comparable to the
chemical-shift difference Δω** between those environments — the *intermediate
exchange* regime (µs–ms). Move faster (Δω ≪ kₑₓ) and the peak sharpens back up as
a population-weighted average; move slower and you see two peaks. So a missing
peak is not "disorder" — it is a **timescale-selective reporter of µs–ms
conformational exchange**. Everything below follows from that.

## The non-obvious strong correlates (what you asked for)

These are real, documented in the paper, and *not* what people first reach for:

1. **Sequence conservation.** The paper's headline structural correlate: residues
   with µs–ms exchange are **more evolutionarily conserved** than average, and
   missing-peak residues are statistically indistinguishable from measured-Rex
   residues on this axis (Fig 1e). The logic is inverted from intuition — you
   don't get slow dynamics *because* a residue is conserved; the residue is
   conserved *because* the slow motion it enables (catalysis, allostery, gating)
   is functional. Conservation is a proxy for function, and function is what
   drives µs–ms exchange.

2. **Where a protein's ensemble moves (MD substates).** For BPTI, the five
   kinetically-distinct substates from the DE Shaw 1-ms simulation map onto
   exactly the two loops Dyna-1 flags (AUROC 0.92, Fig 4c). The predictive signal
   is *where the ensemble visits multiple basins*, not amplitude of motion.

3. **Apo↔holo conformational difference.** Residues whose position differs between
   the apo and ligand-bound crystal structures are the ones that light up — e.g.
   MptpA loops that differ between apo 2LUO and holo 1U2P (Fig 4f). A residue that
   occupies two environments across two crystals is, unsurprisingly, one sampling
   both in solution.

4. **Enzyme lid / catalytic-loop opening — even in the apo state.** Adenylate
   kinase hinges and lid, K-Ras Switch I/II, MptpA P-loop, DUSP3 variable-insert
   loop (Fig 5e). Lid open↔closed *is* a µs–ms exchange process, so the lid
   broadens out before you ever add substrate.

5. **Fast-µs R₂ that CPMG cannot suppress.** Residues in exchange too fast for
   CPMG relaxation-dispersion (Δω≈kₑₓ at the µs end) are invisible to the standard
   experiment but still broaden the peak. Adding these labels raised Dyna-1 AUROC
   in 5 of 6 CPMG sets (BlaC 0.65→0.72, Fig 5) — a signal conventional dispersion
   analysis discards.

6. **Disulfide-bond isomerization.** BPTI's Cys14/Lys15/Cys38/Arg39 broaden from a
   known millisecond disulfide-bond transition — a specific slow chemical switch,
   not generic flexibility.

## The myths — features people assume predict missing peaks, but don't

These are the ones worth flagging to an audience, because the whole field reaches
for them and the paper shows their distributions are **flat** (assigned vs
unassigned residues look the same):

- **Crystallographic B-factor.** Similar distributions for assigned vs unassigned
  (Fig 2h). B-factor conflates lattice disorder, refinement, and fast (ps–ns)
  wobble — almost none of which is µs–ms exchange.
- **Missing electron density in X-ray / cryo-EM.** Residues unresolved in a
  crystal or map are *distinct* from residues with missing NMR peaks (Fig 2f,g) —
  little overlap. Static disorder ≠ slow exchange.
- **AlphaFold2 pLDDT.** Low pLDDT tracks ps–ns motion and static disorder, not
  µs–ms exchange (Ext Data Fig 2). A confidently-folded residue can be highly
  dynamic on the slow timescale, and a low-confidence one often isn't.
- **Amino-acid identity alone.** A naive AA+DSSP classifier scores AUROC 0.501 —
  random (Fig 3c). Composition carries no dynamics signal without structural
  context.

## Confounders — things that create *false* missing peaks

Real broadening, but not the protein's intrinsic functional dynamics; the paper
had to control for each:

- **Phosphate buffer + a phosphate-binding protein** — 14 of the 29 worst-AUROC
  proteins bind phosphate and were run in phosphate buffer; buffer-ion exchange
  broadens surface residues (Ext Data Fig 7).
- **Incomplete amide back-exchange** in deuterated samples (removed in curation).
- **ps–ns fast motion** at a single field strength (can masquerade; needs multi-field to separate).
- **Aromatic ring-flipping** — a µs–ms process not tied to backbone function; a
  genuine Dyna-1 blind spot (NtrC Tyr101 missed).
- **Peak overlap / spectral crowding, His-tag residues, prolines** — trivial
  non-dynamics reasons a peak is absent.

## How to use this

If the goal is to find functional µs–ms dynamics from structure alone, **rank by
conservation + ensemble-displacement + apo/holo difference, and explicitly
*ignore* B-factor and pLDDT** — the opposite of the usual flexibility heuristics.
That inversion is the shareable, non-obvious finding.
