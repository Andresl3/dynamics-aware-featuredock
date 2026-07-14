# Domain-expert-conditioned search vs. Claude-on-its-own

**Question.** When you ask Claude Science to scout dynamics-dark drug targets, does it
matter *how* you frame the ask? Specifically: does conditioning the search on a domain
expert's judgment — "read the literature as if you were Dr. Dorothee Kern" — produce
materially better candidates than letting Claude optimize the problem on its own terms?

**Setup (both runs, same session, same tools).** Both searches used the same live
connectors (PubMed counts, ChEMBL target/bioactivity lookups) and the same target
universe. The only variable was the *prompt frame*:

- **Unconditioned (Claude solo).** Claude was free to define and maximize its own
  objective. It built a computable gap score — roughly *disease-literature volume ÷
  dynamics-literature volume* — and ranked the proteome by it. Top picks:
  **GLS, NAMPT, GAPDH, TYMS, PKM.**
- **Expert-conditioned (as Kern).** The prompt asked for the qualitative filter a
  biophysicist actually applies: *the protein's function must be a conformational
  switch, its motion must be unmeasured, and it must not already be a crowded drug
  program.* Top picks: **ACO1/IRP1, SHMT2, NADSYN1, ALDH1L2.**

Every number below was pulled live this session (PubMed `total_count` per query;
ChEMBL target existence). No values are recalled.

## Result — the two searches land in different regions

| metric (mean per candidate) | unconditioned | expert-conditioned | fold |
|---|--:|--:|--:|
| dynamics papers (conf.+MD+NMR) | 242 | 4 | **61×** |
| inhibitor-program papers | 759 | 41 | **19×** |
| clinical papers | 201 | 8.5 | **24×** |
| disease-literature papers | 1513 | 74 | 20× |
| already drugged (has ChEMBL target) | **2 / 5** | **0 / 4** | — |

The unconditioned score is dominated by a numerator it can measure well —
disease-literature *volume* — so it rewards proteins that are famous for other reasons.
GLS and GAPDH each carry **200–900 dynamics papers** and **1,000+ inhibitor papers**;
GLS is already a clinical-stage target (ChEMBL CHEMBL2146302, 35 potent actives). These
are not dark. The score mistook *fame* for *opportunity* because volume is the easiest
thing to count.

Expert-conditioning inverts the objective. Every expert pick sits in the **open lane**
(Fig. panel a, shaded): near-zero dynamics literature, thin inhibitor programs, and
**no ChEMBL target record at all**. NADSYN1 and ALDH1L2 have a literal **0/0/0** on
conformational-change, MD, and NMR papers, yet carry decisive disease genetics and
mouse biology. That combination — real biology, zero motion data, undrugged — is
exactly what a Dyna-1 → NMR program can claim, and it is precisely what a
volume-maximizing score filters *out*.

## Why the conditioning works (and why it isn't just "smaller numbers")

The expert filter encodes three constraints Claude's own score could not express as a
computable quantity:

1. **"Function *is* a switch."** Kern doesn't want any under-studied enzyme — she wants
   one whose therapeutically relevant behaviour is the *rate and population of a
   conformational transition* (ACO1's Fe-S ⇌ RNA-binding switch; SHMT2's dimer⇌tetramer
   gate). Literature volume cannot see this; it takes reading the biology.
2. **"Unmeasured, not just under-published."** The expert distinguishes a protein no one
   has *looked at* dynamically from one that is simply less popular. The 0/0/0 targets
   are dark by measurement, not by neglect of a well-trodden target.
3. **"Not already crowded."** The `has_target` check is the quantitative shadow of a
   judgment — *is there already a medicinal-chemistry program here?* Expert picks score
   0/4; solo picks 2/5.

The lesson is not "expert prompt = fewer papers." It is that **the expert frame supplies
the objective function Claude cannot derive from counts alone.** Left to optimize a
measurable proxy, an agent climbs the proxy — and disease-literature volume is a proxy
that peaks on the *most* studied proteins, the opposite of the intent. A short,
well-aimed piece of domain conditioning ("as Kern, function-is-a-switch, undrugged")
redirected the same tools and the same model to a 20–60× less-crowded, entirely
undrugged shortlist.

## Caveat

This is a **4–5 candidate per arm** comparison, not a benchmark. The fold-changes are
large and consistent across three independent literature axes, but the claim is
directional ("conditioning moves the search into the open lane"), not a powered effect
size. The honest framing for the judges: *domain-expert conditioning is a lever on where
the agent looks, and here it moved the search off the crowded proteins the naive
objective rewarded and onto genuinely dark, undrugged, biology-rich targets.*

---
*Grounding: PubMed per-query `total_count` and ChEMBL target lookups pulled live this
session (`handoff/conditioning_ab.json`). Candidate briefs:
`dynamics_scouting_brief.md` (ACO1/SHMT2) and `dark_biologyrich_brief.md`
(NADSYN1/ALDH1L2).*
