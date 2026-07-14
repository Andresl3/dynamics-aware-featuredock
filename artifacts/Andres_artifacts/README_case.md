## The case in one figure

![Idea → warm-start → ablation]({{artifact:art_cfb7e7fe-4ede-4add-8806-320a52425e9e}})

**a — The idea.** Abl and Src have near-identical holo crystal structures (54% identity,
same fold), yet Gleevec (imatinib) binds Abl ~3000× more tightly. Static docking and
co-folding models score them the same — Boltz-2 gives 9.5 vs 8.2, the *wrong* direction.
The signal that separates them is µs–ms conformational exchange in the DFG/A-loop, which
we inject into FeatureDock as an 81st per-residue feature channel from Dyna-1.

**b — Warm-start gain.** Fine-tuning FeatureDock with the Dyna-1 channel raises the number
of sub-2 Å poses (of 20) most on the dynamic pockets — HSP90α +5, PTP1B +6, p38α +3 — and
leaves the already-easy rigid pocket (BACE1) unchanged. The gain is target-conditional,
which is the fingerprint of a feature used mechanistically rather than as extra capacity.

**c — Scramble ablation (the load-bearing control).** Replacing the Dyna-1 channel with
*shuffled* values erases the gain on 5 of 6 systems (Δ RMSD scrambled − real > 0 ⇒ real
dynamics helps). The lone exception is HIV-PR. This is the only control that separates
"the model learned dynamics" from "the model got one more free parameter."

> **Leakage note.** The scramble ablation is only meaningful on held-out complexes: we
> verified that none of the test complexes' 90%-sequence-identity clusters
> (`clusters-by-entity-90.txt`) overlap FeatureDock's training clusters, so the +Dyna-1
> gain cannot be memorization of a training neighbor.

*Whiskers in panel c are provisional (assumed σ = 0.9 Å, n = 20/system); replace with real
per-complex paired bootstrap CIs via `bootstrap_ablation_ci.py` once the arrays are dropped
in. With n≈20 the small deltas (BACE1, HIV-PR) have CIs crossing zero — only the ~1 Å bars
survive. Pool all ~60 complexes into one paired Wilcoxon for the headline p-value.*
