# Does Dyna-1 p_exchange predict conformational-state change?

**Question (as posed):** given the Dyna-1 per-residue exchange predictions on
PDBbind_2021v structures (the `dyna1_csv` file), does a region of high
p_exchange correspond to a region that actually adopts a different
conformational state (open/closed, alternative state) — the kind of motion
CoDNaS catalogs? And, at the protein level, does Dyna-1 tell a mostly-static
protein apart from an open/closed one?

## How this was measured (no CoDNaS server needed)
CoDNaS was down (HTTP 503 for the whole session), so conformational diversity
was **reconstructed directly from the PDB**, which is exactly what CoDNaS does
internally:

1. All **5,299** PDBbind structures in `dyna1_csv` → mapped to UniProt via the
   RCSB GraphQL API (**5,244** mapped → **1,537** proteins; **194** have ≥6
   structures).
2. For 55 of the richest multi-structure proteins (≤25 structures each), all
   Cα coordinates were Kabsch-superposed onto the largest structure over shared
   residue numbering, and **per-residue displacement across the ensemble**
   (max / mean / std) was computed. This displacement IS the CoDNaS-style
   "does this residue change state" signal. Median per-protein maximum
   displacement = **10.1 Å**; 41/55 proteins have a residue moving >5 Å — these
   are genuine open/closed ensembles, not ligand-swap noise.
3. Each reference structure's Dyna-1 `p_exchange` was joined per residue →
   **14,675 residue observations across 55 proteins**.

## Result — the two questions give opposite answers

**Per-residue (which residues move?): essentially no correlation.**
- Pooled Spearman ρ(p_exchange, max displacement) = **−0.083** (n=14,675).
- Mean *within-protein* ρ = **+0.033**, median **+0.008**; only 11% of proteins
  reach ρ>0.2, and 46% are negative.
- Restricting to the well-ordered core (termini stripped) of the 45 proteins
  that genuinely change state (>3 Å): pooled ρ = **−0.080**, mean within-protein
  ρ = **+0.018**.
- High-p_exchange residues (≥0.5) do **not** move more: median displacement
  0.80 Å vs 0.96 Å for low-p_exchange; AUROC = 0.46.

→ **Dyna-1 p_exchange does not localize to the residues that swing between
conformational states.** A high-p_exchange patch is not a reliable pointer to
the hinge/lid/loop that actually moves.

**Per-protein (is this protein a mover?): moderate positive.**
- mean p_exchange vs max displacement: Spearman ρ = **+0.293**, Pearson r =
  **+0.277** (n=55 proteins).

→ Proteins Dyna-1 scores as globally more exchangeable *are* more likely to
contain a large conformational change somewhere. As a whole-protein
"static vs dynamic" flag it carries real, if moderate, signal.

## Why this is the expected — and honest — answer
The two observables live on **different timescales and geometries**:
- Dyna-1 predicts **µs–ms chemical exchange** — a residue sampling ≥2 magnetic
  environments (Δω on the order of the exchange rate). That is a *local*
  reporter of an invisible excited state; it does not have to sit on the atom
  that translates the furthest.
- CoDNaS/PDB displacement is a **geometric** quantity — how far a Cα moves
  between two crystallized end states. The residues with the largest Cα
  translation are typically rigid-body lid/domain tips that move *as a unit*;
  the residues that *gate* the transition (and light up in exchange) are often
  at the hinge, buried, and barely translate.

So p_exchange and Cα displacement measure related but distinct things: exchange
marks *where the kinetic barrier is felt*, displacement marks *what physically
swings*. They coincide at the protein level (a protein with a real excited
state tends to have a real alternative structure) but decouple residue-by-residue.

## What this means for the project
- **Use Dyna-1 as a protein-level triage flag** ("does this target have a
  hidden state worth modeling?") — ρ≈0.3 supports that use.
- **Do not** use raw per-residue p_exchange as a map of *where* the alternative
  conformation is. To localize the moving region you still need an ensemble
  method (MD, CoDNaS/PDB superposition, cryptic-pocket detectors).
- This is consistent with the earlier RelaxDB finding: per-residue conservation
  and simple structural features are weak per-residue predictors too; the
  useful signal is aggregate, not pinpoint.

## Files
- `dyna1_vs_conformational_diversity.png` — 3-panel figure (A per-residue
  hexbin, B within-protein ρ histogram, C per-protein scatter).
- `dyna1_codnas_residues.csv` — 14,675 rows: uniprot, ref PDB, resid, n_states,
  p_exchange, disp_max/mean/std.
- `dyna1_codnas_perprotein.csv` — 55 proteins: mean_pex, frac_hi, max_disp,
  mean_disp.

## Caveats
- Ensembles were built from PDBbind members of each protein (holo-biased,
  ≤25 structures/protein); a full CoDNaS pull would add apo states and more
  proteins, likely strengthening panel C but not changing the per-residue
  conclusion (the timescale/geometry mismatch is structural, not a sampling
  artifact).
- Displacement is Cα-only; side-chain rotameric exchange (which Dyna-1 can also
  reflect) is invisible to this metric, which if anything *lowers* the
  per-residue correlation ceiling.
