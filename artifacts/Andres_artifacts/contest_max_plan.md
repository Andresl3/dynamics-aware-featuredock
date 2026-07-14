# Plan to maximize the score — Dyna-1-FeatureDock (Abl/Src de-risked)

## The reframe (do this first, everything else depends on it)
- **Headline claim (defensible):** "A µs–ms per-residue dynamics channel improves
  FeatureDock pose prediction — most on dynamic proteins — and a scrambled-channel
  ablation proves the *dynamics* is doing the work, not the extra capacity."
- **Abl/Src status:** motivation only. One sentence: "this is the class of
  selectivity static structure misses." Never a claimed result, no RMSD bar
  labeled Abl/Src, no "we resolve the paradox." Measured fact that forces this:
  imatinib-contact p_exchange is flat (Abl 0.461 / Src 0.471, holo).
- **What you are NOT claiming:** beating Boltz-2/DiffDock on affinity; solving
  selectivity; any wet-lab result. Claiming less, proving it fully, scores higher
  than claiming more and getting challenged.

---

## Demo — 30 pts — HIGHEST LEVERAGE, build this first
Target: 27–30. A figure is not a demo; judges reward *working + trustworthy + cool
to watch*. Build ONE live thing and make it bulletproof.

**Primary demo — the live ablation (this IS the science, watched):**
1. On stage, one held-out dynamic target (p38α — your strongest bump).
2. Run docking with (a) real Dyna-1 channel, (b) scrambled channel, (c) no channel.
3. Show top-1 RMSD drop with real, and the drop *vanishing* under scramble.
4. Punchline line: "if the number survived a scramble, we'd have nothing — it doesn't."
- Pre-compute all three so the "live" run is <30 s (load cached tensors, not a
  cold GPU). Rehearse the failure mode: if the run hangs, have the recording.

**Secondary (backup / B-roll):** `dynamic_selectivity_score.py` runs live —
type target + drug footprint → DSS + per-residue exchange plot. Already validated.

**Deliverable:** 30-second screen-capture of the live ablation, embedded in the
3-min video + runnable in person. Checklist: no cold starts, no network calls
mid-demo, every number on screen traceable to a file.

---

## Impact — 25 pts — make the numbers unarguable
Target: 20–22. Current weakness: n=20×3, no CIs, no baseline comparison.
1. **Pool all 60 complexes, paired test.** Each complex scored by both arms →
   Wilcoxon signed-rank on per-complex RMSD (baseline vs +Dyna-1). One p-value
   across 60 beats three underpowered per-target ones.
2. **Bootstrap CIs** (1000× resample complexes) on ΔRMSD and Δsuccess-rate, per
   target and pooled. Report "ΔRMSD = −0.X Å [95% CI −a, −b]."
3. **Dynamic-vs-rigid split.** Rank the 60 by protein dynamics (mean p_exchange or
   your RelaxDB frac_rex); show the gain is larger in the dynamic half. This is
   your *mechanistic* impact claim and it's testable in your own data.
4. **One baseline panel:** FeatureDock-Dyna-1 vs DiffDock (you have DiffDock AUC
   0.76 vs FD 0.74 already) on the same complexes. Don't overclaim — "competitive
   on pose, and the dynamics channel is orthogonal signal any of them could add."
5. **Package the reusable object:** the +1 channel as a one-command add-on + the
   score. "Others can bolt this onto their own docker" is the build-on claim.

---

## Claude Use — 25 pts — sell the method, not the code
Target: 20–23. "Wrote code + found targets" is the floor. Your genuinely novel
Claude use is the **multi-session experimental loop** — one session designing the
ablation and the falsification tests that another session executes. Foreground it.
1. **Show the orchestration explicitly** in the writeup/video: session A (design +
   critique + hypotheses) → session B (run) → session A (grade against rubric,
   catch the Abl/Src flatness). That self-correction is the surprising capability.
2. **The Abl/Src catch is a Claude-Use highlight, not a failure to hide:** "Claude
   measured our own flagship's feature, found it flat in the holo state, and told
   us to change the story." Judges reward teams whose tooling caught their own
   error. This is worth more than a novel compound.
3. **Compounds (optional, high-risk):** only if every molecule has a real
   ChEMBL/BindingDB ID + measured activity + shown off-target prediction. A
   fabricated "novel" compound is instantly falsifiable and sinks credibility.
   Skip it rather than fake it.

---

## Depth & Execution — 20 pts — you're closer than you think
Target: 17–18. Your arc already IS "past the first idea": Dyna-1 channel →
warm-start fine-tune → real-vs-scrambled ablation. Judges only miss it if you
don't present it as one story.
1. **One 3-step figure:** idea → warm-start → ablation, ablation as punchline.
2. **Leakage check (do it, state it):** confirm none of the 60 test complexes'
   90%-identity clusters are in FeatureDock's training clusters (you have
   `clusters-by-entity-90`). One sentence: "held-out at 90% identity, verified."
3. **Show the honest negative:** the holo Abl/Src flatness and the per-residue
   CoDNaS decoupling (ρ≈0) you already found. A team that reports what *didn't*
   work reads as craft, not hack.

---

## 48-hour execution order (highest score-per-hour first)
1. **(Demo)** Build + rehearse the live ablation. — biggest axis, currently 0.
2. **(Impact)** Pooled paired test + bootstrap CIs across 60 complexes. — turns a
   soft claim into a hard one; ~2 h of stats on data you already have.
3. **(Depth)** The 3-panel idea→warmstart→ablation figure + leakage sentence.
4. **(Impact)** Dynamic-vs-rigid split panel + DiffDock comparison panel.
5. **(Claude Use)** Writeup section on the multi-session loop + the Abl/Src catch.
6. **(Reframe)** Scrub every deliverable (summary, video script, slides, repo
   README) to demote Abl/Src to motivation. Grep for "3000×", "paradox",
   "resolve" and soften each.
7. **(Optional)** Apo-state Abl/Src test — ONLY as a "future work / preliminary"
   slide, not a claimed result. If it shows signal it's a bonus; if flat, it
   stays in future work and costs you nothing.

## What "100%" realistically means here
A clean 100 is not the goal — no judge gives it. The goal is to remove every
place a sharp judge can say "but you didn't show X." This plan closes: no CIs
(→ bootstrap), no baseline (→ DiffDock panel), no leakage statement (→ verified),
first-idea perception (→ ablation-as-punchline), overclaim on Abl/Src (→ demoted),
no live demo (→ live ablation). Do those and you are a genuine top-tier entry:
realistically **82–90**, with Demo execution the swing factor.
