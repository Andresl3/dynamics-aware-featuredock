# Repo integration guide — Dynamics-aware FeatureDock

Where every deliverable from this planning session goes in
`github.com/natesana/dynamics-aware-featuredock` (branch `main`, MIT).

The goal: a judge cloning the repo should hit the Abl/Src story in the first
screen of the README, and every figure/claim should be one click from its
source. Nothing here is model output — the repo's hypothetical-results honesty
banner stays until the model is trained.

---

## 1. Proposed repo layout for these assets

```
dynamics-aware-featuredock/
├── README.md                      ← lead with the paradox + Fig 1 (see §2)
├── docs/
│   ├── framing_brief.md           ← judge-facing strategic brief
│   ├── abl_src_experiment.md      ← flagship protocol (PDBs, ΔScore metric)
│   └── figures/
│       ├── gleevec_paradox.png            (Fig 1)
│       ├── gleevec_mechanism.png          (Fig 2)
│       ├── dynamics_timescale.png         (Fig 3)
│       ├── target_impact_landscape.png    (target landscape)
│       └── abl_src_result_template.png    (labeled MOCK result)
├── data/
│   ├── flexible_docking_benchmark.csv     (18-target Dyna-1 benchmark)
│   ├── target_impact_landscape.csv        (scored, UniProt+AlphaFold IDs)
│   └── pdb_verify.csv                     (RCSB verification log)
└── slides/                        ← 3-min video / demo assets
    ├── abl_src_01_dynamics_challenge.png
    ├── abl_src_02_not_ground_truth.png
    ├── abl_src_03_nmr_crash_course.png
    ├── abl_src_04_missing_peaks.png
    └── abl_src_05_dyna1_room.png
```

## 2. README top-of-file (the 15-second pitch)

Open with the thesis and Fig 1 immediately:

```markdown
# Dynamics-aware FeatureDock
**Two kinases that look identical in every crystal structure bind the same
blockbuster drug 3,000× differently — and the reason is motion no current
docking or co-folding model can see.** We give FeatureDock that missing sense
by feeding it Dyna-1's µs–ms flexibility predictions.

![The Gleevec selectivity paradox]({{artifact:art_86b138a6-5e40-4815-b7a6-989266f83908}})

Abl binds Gleevec at 80 nM; Src ~3,000× weaker — yet their imatinib-bound
crystal structures superimpose. Boltz-2 scores them 9.5 vs 8.2 (can't separate).
The discriminating signal is a µs–ms induced-fit step (Kern 2014). → see
[docs/framing_brief.md](docs/framing_brief.md).
```

## 3. Where the Abl/Src slides go

The 5 rendered slides in `slides/` are the **video/demo spine** — they are the
visual narrative for the 3-minute submission video (Demo = 30% of score):

| Slide | Beat in the 3-min video |
|-------|-------------------------|
| 01 dynamics_challenge | The hook: structure is cheap, motion is invisible |
| 02 not_ground_truth   | Why a single crystal misleads |
| 03 nmr_crash_course   | How we *know* motion exists (µs–ms exchange) |
| 04 missing_peaks      | The blind spot static models share |
| 05 dyna1_room         | Dyna-1 fills the room → our method |

Drop them in `slides/` and reference them from a `slides/README.md` storyboard,
or embed directly in the video editor. They pair with Fig 1–3 (`docs/figures/`)
which are the *paper-grade* versions of the same argument.

## 4. Artifact → repo-path map

| Artifact (this session) | Repo destination | Role |
|---|---|---|
| framing_brief.md | docs/ | judge-facing strategy (Impact/Depth/Demo/Claude-use) |
| project_summary.md | README appendix or CONTEST_SUMMARY.md | 100- & 150-word contest summary |
| gleevec_paradox.png | docs/figures/ | Fig 1 — the paradox (README hero) |
| gleevec_mechanism.png | docs/figures/ | Fig 2 — two-step induced-fit landscape |
| dynamics_timescale.png | docs/figures/ | Fig 3 — the timescale gap |
| target_impact_landscape.png/.csv | docs/figures/ + data/ | where dynamics pays off |
| abl_src_result_template.png | docs/figures/ | labeled MOCK of the expected win |
| abl_src_experiment.md | docs/ | flagship protocol + verified PDBs |
| flexible_docking_benchmark.csv | data/ | 18-target Dyna-1 benchmark |
| flexible_docking_benchmark.png | docs/figures/ | benchmark overview |
| pdb_verify.csv | data/ | provenance: every PDB checked vs RCSB |

## 5. Honesty banner (keep as-is)

Every results section and figure caption must retain wording equivalent to:

> **No model is trained yet.** `abl_src_result_template.png` shows the *expected
> shape* of the outcome, not measured scores. The benchmark and target landscape
> use published experimental data (NMR µs–ms, K_D) and transparent 1–5 rubrics —
> not model predictions.

This is a Researcher-Track *proposal*: the science, the plan, and the test
harness are the deliverable. Overclaiming would cost more Depth points than the
honest framing costs Demo points.

## 6. Suggested commit sequence

1. `docs/` + figures → README hero image works.
2. `data/` CSVs → benchmark + landscape reproducible.
3. `slides/` → video assets in place.
4. Update root README with §2 opener + links.
5. Tag `v0.1-proposal`.
