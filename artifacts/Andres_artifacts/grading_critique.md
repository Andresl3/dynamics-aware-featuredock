# Tough-grading self-assessment — Dyna-1-FeatureDock

Graded hard, as requested. Where I disagree with your self-score I say why.
Bottom line up front: **~54–58 / 100 as it stands today**, and the gap to a
winning score is almost entirely **Demo (30%)** and **closing the Abl/Src
credibility gap**, not more model runs.

| Axis | Weight | Your read | My tough read | Why |
|---|---|---|---|---|
| Impact | 25 | ~25 | **15–17** | Real directional result, but rests on n=20×3 + one ablation, small magnitude, and the flagship (Abl/Src) is untested. |
| Claude Use | 25 | 10 (→25 w/ drug) | **10–13** | Code + target-finding is baseline. The novel-compound plan can raise it — or sink it if the compounds are unverifiable. |
| Depth | 20 | unsure | **13–15** | The ablation (real vs scrambled p_exchange) IS "past the first idea." Your problem is narrative, not craft. |
| Demo | 30 | TBD | **15 (assume)** | Biggest single axis, currently unknown. This is where the marginal hour pays most. |

## The landmine: you lead with Abl/Src but you tested p38/HSP90/CA-II

- Measured from Dyna-1's own PDBbind p_exchange: imatinib-contact residues have
  mean **0.461 on Abl (3PYY) vs 0.471 on Src (2OIQ)**; **zero** residues > 0.6 in
  either; CDK2 apo (1b38) and holo (1e1x) pocket exchange identical to 3 dp
  (0.517). **The bound-state feature does not distinguish Abl from Src.**
- So the honest claim is: "the dynamics channel improves pose prediction, most on
  dynamic proteins (p38/HSP90/CA-II), and a scrambled channel does not" — that is
  a *docking* result. It is **not** "we resolve the Gleevec selectivity paradox."
- **If you keep Abl/Src as the headline, you must either (a) actually run the
  apo-state test** (Dyna-1 on 2g1t/2src, score the imatinib footprint — the one
  experiment that could show signal where the holo is flat), **or (b) demote
  Abl/Src to "the motivating problem" and make p38/HSP90/CA-II + the ablation the
  result.** Do not let the two blur; tough judges read that as overclaiming.

## Impact — 15–17/25 (you said ~25)

What others can build on *today*: a dynamics-channel augmentation that helps
docking, with an ablation showing the signal is the dynamics, not capacity. That
is a legitimate finding. Why it isn't 25 yet:
- Magnitude is a few complexes per target (9/20→12/20). No CIs shown.
- No head-to-head vs the models you name (DiffDock, Boltz-2) *on your targets*.
  Your prompt claims an edge over them; your figure doesn't show them.
- The reusable object (the score / the channel) isn't packaged for others to run.
**To reach ~22:** pooled paired test + bootstrap CIs across all 60 complexes;
one panel putting FeatureDock-Dyna-1 next to DiffDock/Boltz-2 on the same
complexes; ship the channel as a one-command add-on.

## Claude Use — 10–13/25 (you said 10, →25 with a drug)

Honest: "wrote code + found targets" is the floor — every team does that. What
would actually surprise judges is **the ablation loop and multi-session
orchestration you're already doing** (using one Claude session to design the
experiment another runs). Foreground that as *methodology*, it's more novel than
a compound name. **Caution on the drug plan:** point 5 of your prompt asks for
compounds with "little to no prior research" + "predicted weak off-target." That
is the easiest thing in this whole project to fabricate and the easiest for a
knowledgeable judge to falsify. A shallow, unverifiable compound *lowers* your
credibility. If you do it, ground every compound in a real ChEMBL/BindingDB
record with a measured activity, and show the off-target prediction, or don't
show it. A verified real compound beats a novel-sounding fake every time.

## Depth — 13–15/20 (you're underrating yourselves)

Your arc — Dyna-1 channel → warm-start fine-tune → **real-vs-scrambled ablation**
— is exactly the "wrestled with it" evidence the rubric rewards. The scrambled
control is the single most sophisticated thing you did; it's what separates
"correlation" from "the feature is doing work." Judges will only see "first idea"
if you *present* it as one figure. Fix = a 3-step slide: idea → warm-start →
ablation, with the ablation as the punchline.

## Demo — the 30% you're leaving on the table

This is worth more than Impact or Claude Use individually and it's your TBD. A
figure is not a demo. Options, cheapest first:
1. **Live score:** `dynamic_selectivity_score.py` already runs — type a
   target + drug footprint, get a DSS and the per-residue exchange plot, live.
2. **Live A/B pose:** show baseline vs +Dyna-1 docking one held-out dynamic
   complex, side by side, with the RMSD dropping — watchable in 20 seconds.
3. **The ablation, live:** run real vs scrambled channel on one target on stage;
   the gain vanishing under scramble is the "genuinely cool to watch" moment.
Pick one and make it bulletproof; 30 points rewards *working + trustworthy*.

## On the prompt you're about to send another session

It's well-constructed, but two asks will produce answers that hurt you if used
uncritically:
- **Point 3 (scoring-function fix for Abl/Src):** any proposal that reads
  p_exchange on the *holo* pocket is dead on arrival (it's flat, measured above).
  Constrain the other session to a mechanism on the **apo / accessible state** or
  a **Δ(apo−holo) exchange** term.
- **Point 5 (novel compounds):** as above — demand real database records, not
  plausible-sounding novelty. Add to the prompt: "every compound must have a
  verifiable ChEMBL/BindingDB ID and a measured activity value; do not propose
  compounds you cannot ground in a real record."
