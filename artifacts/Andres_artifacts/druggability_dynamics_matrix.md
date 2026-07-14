# Protein dynamics × therapeutic-candidate properties

**What this is (and isn't).** You asked me to correlate Dyna-1 dynamics with
drug-candidate properties — off-target effects, selectivity, affinity, efficacy,
toxicity, antibody motion, difficulty-to-drug, cost, cryptic pockets. I want to
be precise about the epistemic status: **there is no paired dataset** that links
Dyna-1 per-residue exchange scores to these outcomes, so I cannot fit a real
correlation coefficient today. What I *can* give — rigorously — is a
**mechanistic map** grounded in the primary literature: for each property, does
µs–ms conformational dynamics (the thing Dyna-1 predicts from missing NMR peaks)
causally inform it, how, and how strongly. The honest "no" answers matter as much
as the "yes" answers, because the failure mode of this whole area is overclaiming.

Companion files: `druggability_dynamics_matrix.csv` (14 properties, per-property
mechanism + evidence) and `druggability_dynamics_matrix.png`.

## Strongly dynamics-informed — the real value

1. **Cryptic / transient binding pockets.** The single biggest payoff. A pocket
   that is closed in every crystal but opens in a lightly-populated µs–ms state is
   invisible to static docking — this is the textbook reason a target gets called
   "undruggable." Dyna-1 flags the pocket-lining residues that are in exchange.
   Precedent: the KRAS switch-II pocket (undruggable for 30 years → sotorasib);
   PocketMiner (Meller & Bowman 2023) predicts cryptic sites directly from
   dynamics.

2. **Conformational-state selectivity.** Two proteins with near-identical pockets
   can bind a drug 1000× differently because one can *reach* the drug-compatible
   conformation and the other can't. This is the Abl/Src/imatinib story (Kern
   2014): identical DFG-out pocket, 3000× affinity gap, entirely from the µs–ms
   equilibrium. Static co-folding (Boltz-2) scores them 9.5 vs 8.2 — can't see it.

3. **Allosteric-site druggability.** Allosteric pockets are *defined* by coupled
   slow motion, not by a static cleft. You cannot identify them, or predict
   whether ligand binding will propagate, without the dynamics (PTP1B, SHP2).

4. **Binding affinity — the state-weighted part.** Thermodynamic ΔG has two
   factors: intrinsic fit to the bound-state pocket (static methods do this) ×
   population of the accessible bindable state (only dynamics does this). When
   pockets are degenerate, the second factor dominates and static scoring fails.

5. **Drug residence time / off-rate (kₒff).** Residence time predicts in-vivo
   efficacy better than Kd (Copeland), and it *is* a µs–ms kinetic quantity —
   slow induced-fit closure is exactly what lengthens it. This is the most
   under-appreciated hard link between dynamics and a property people care about.

## Partial — dynamics is one input among several

- **Family selectivity & off-target effects** — sequence/pocket differences do
  most of the discrimination; dynamics resolves the degenerate cases (shared
  DFG-out accessibility drives kinase polypharmacology).
- **Resistance-mutation liability** — gatekeeper/allosteric mutations (Abl T315I)
  often act by *shifting the conformational equilibrium* a drug depends on,
  changing no direct contact. A dynamics effect, but one of several resistance
  mechanisms.
- **Antibody CDR motion** — CDR-H3 and framework loops genuinely undergo µs–ms
  exchange, and loop flexibility tracks polyreactivity/aggregation and affinity
  maturation. But developability also has drivers dynamics can't see (charge
  patches, hydrophobic SASA), so it's a partial input, not a verdict.
- **Cellular efficacy** — dynamics touches it only through engagement + residence
  time; the rest is pathway biology and PK.

## NOT dynamics-informed — honest limits (and the trap)

- **Toxicity endpoints (hERG, DILI, reactive metabolites)** — these are channel
  pharmacology, metabolism, and immune biology. Dynamics informs *only* the
  off-target-binding sliver upstream, never the endpoint. Claiming otherwise is
  overreach.
- **Cost / difficulty to MANUFACTURE** — synthesis route, CMC, formulation, trial
  size. Zero protein-backbone-dynamics content. Note the category error to avoid:
  *difficulty-to-drug* (how hard the target is to hit — genuinely
  dynamics-informed) is **not** *difficulty-to-make* (a process-chemistry
  problem).
- **Oral bioavailability / ADME-PK** — set by ligand physicochemistry (logP, PSA,
  solubility), not the target's motion.
- **Potency scored against a single static structure** — this is the *anti*-signal.
  Docking one crystal and ranking by score is precisely the method that misses
  dynamics; it's why Abl≈Src on static score despite the 3000× real gap. The
  property people most often compute is the one dynamics most often contradicts —
  which is the entire thesis of the project.

## The takeaway for triaging a therapeutic candidate

Use dynamics for the **target-side, state-dependent** questions — is there a
cryptic or allosteric pocket, can I get conformational selectivity, will off-rate
be long, why do two look-alike targets differ. Do **not** use it for
**ligand-side or organism-side** questions — PK, tox endpoints, manufacturing
cost. The clean rule: *dynamics tells you whether and how a target can be
hit; it does not tell you what happens to the molecule after it's made.*

## To turn this into a real correlation (offered)

The rigorous next step, if you want numbers instead of a mechanistic map: join
Dyna-1 scores for a target panel (e.g. the kinases we already have — Abl, Src,
CDK2, p38) to (a) ChEMBL selectivity ratios, (b) measured koff/residence-time
where available (Copeland datasets), (c) cryptic-pocket annotations from
PocketMiner/CryptoSite. Then compute Spearman ρ per property. That's a bounded
project I can scope if it's useful.
