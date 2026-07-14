# Dynamics-druggable targets at the breast-cancer / T-cell interface

*An analysis connecting the Kim et al. 2021 breast-cancer protein-interaction landscape,*
*the Marson-lab genome-wide CRISPRi Perturb-seq screen in primary human CD4+ T cells,*
*and the "dynamics-aware docking" thesis (FeatureDock + Dyna-1).*

---

## The honest framing first

**The T-cell Perturb-seq dataset is not a breast-cancer dataset.** It is a genome-wide
CRISPRi screen in primary human CD4+ T cells from the Marson lab (4 donors; three states:
Rest, Stim 8 hr, Stim 48 hr; 11,526 gene perturbations; 33,983 perturbation×condition
DE results). It contains no tumour cells and no breast tissue.

Its relevance to breast cancer is **through immuno-oncology**, not through tumour biology:

- T-cell function is the substrate of every checkpoint-inhibitor and adoptive-cell therapy.
- Triple-negative breast cancer (TNBC) is the breast-cancer subtype where immunotherapy
  works, so genes that control CD4+ T-cell activation are directly relevant to how
  well a breast tumour can be attacked immunologically.
- The screen tells us **which genes causally reshape human T-cell state** — i.e. which
  are worth engaging pharmacologically to tune an anti-tumour immune response.

So the question I can answer rigorously is: *which genes are simultaneously (a) causal,
reproducible regulators of human T-cell biology, (b) members of the breast-cancer
protein-interaction network, (c) of a druggable protein class, and (d) governed by the
kind of conformational dynamics that static docking / co-folding models miss and that
Dyna-1-augmented FeatureDock is designed to see?*

---

## Where dynamics enters — and why this dataset makes the case sharper

The Kim et al. breast-cancer paper's central finding is not a target list. It is that
**cancer mutations substantially *rewire* the protein-interaction network** — the same
protein gains and loses partners depending on its mutation state. Rewiring of binding
partners by a point mutation is, mechanistically, a **conformational/dynamics** phenomenon:
the mutation shifts the populations of states the protein samples, exposing or hiding
interaction surfaces and pockets. That is precisely the regime a static crystal structure
cannot capture and a µs–ms dynamics predictor can. The breast-cancer network therefore
supplies not just targets but a *mechanistic reason* dynamics matters here.

The T-cell screen adds the missing axis: **causal functional weight**. A target that is
structurally interesting but functionally inert is not worth the trouble; the Perturb-seq
`n_downstream` (trans-regulatory reach) and cross-donor reproducibility tell us which of
these proteins actually *run* the cell.

---

## The funnel (Figure, panel a)

Starting from every gene perturbed in the screen and narrowing by successive, defensible
filters:

| Stage | Genes | Filter |
|---|---:|---|
| All gene perturbations | 11,526 | screen coverage |
| Reproducible regulators | 1,519 | significant on-target knockdown **and** cross-donor ρ > 0.3 |
| Druggable protein class | 97 | kinase / GPCR / ion-channel / catalytic-receptor / transporter / nuclear-receptor (repo gene lists) |
| Also in BC interaction network | 32 | intersect with 244 genes from the Kim et al. network |
| Dynamics-governed | 4 | documented conformational-dynamics mechanism |

---

## The four flagship targets (Figure, panel b)

Four **kinases** survive every filter — druggable, reproducible T-cell regulators, in the
breast-cancer network, and governed by conformational dynamics:

| Gene | Max trans-reach | Best cross-donor ρ | Condition | Why dynamics matters |
|---|---:|---:|---|---|
| **SIK3** | 1,809 | 0.65 | Stim 48 hr | AMPK-family kinase; activation-loop / DFG dynamics; ATP-site selectivity is hard without capturing the moving state |
| **STK11** (LKB1) | 1,170 | 0.63 | Stim 8 hr | Allosterically activated by the STRAD/MO25 conformational switch — the druggable event *is* a motion |
| **CDK2** | 346 | 0.69 | Stim 48 hr | FeatureDock's own benchmark case: inactive vs active DFG (1B38 vs 6GUE) + a cryptic allosteric pocket |
| **ATM** | 142 | 0.67 | Stim 48 hr | Giant PIKK; autoinhibited-dimer → active-monomer transition gates the ATP site |

These are the targets where "dynamics-aware docking" would change the answer, not just
confirm it. For each, the actionable computational experiment is the same one the hackathon
project proposes for Abl/Src: featurize the alternative conformational states (or a Dyna-1
flexibility-weighted ensemble) and test whether the predicted pocket / binding score
separates the druggable state from the inert one — a separation a single static structure
cannot produce.

Notably, **CDK2 is already FeatureDock's validated case study**, so it is the natural
first target to extend from the drug-docking benchmark into this immuno-oncology context —
zero new infrastructure required.

---

## Broader target context (panel b, grey/green points)

Beyond the four kinases, the 32-gene BC-network ∩ T-cell-regulator set includes the
highest-reach hubs **PTEN** (2,928 downstream, ρ 0.77), **TP53** (1,848, ρ 0.82),
**TSPYL5**, **SMARCB1**, **GATA3**, **CBFB** — canonical breast-cancer genes that are
also among the strongest, most reproducible functional regulators of primary human T
cells. Most are not conventionally druggable (transcription factors, scaffolds), which is
exactly why the druggable-class filter matters and why the four kinases rise to the top.

---

## What I did *not* do (scope honesty)

- I did **not** run docking, Dyna-1, or any structure prediction here. The dynamics
  annotation is a literature-grounded flag on each candidate, not a computed
  flexibility score. Producing the flexibility scores is the proposed next experiment.
- The Perturb-seq screen is CD4+ T cells, not tumour; every claim about breast cancer
  is an immuno-oncology inference, stated as such.
- Cross-donor ρ > 0.3 and the "dynamics-governed" set are analyst choices; they are
  transparent in `tcell_bc_dynamics_targets.csv` (all 1,519 reproducible regulators,
  with druggable class, BC-network membership, and dynamics flag) so the thresholds
  can be moved.

---

## Data sources

- **Perturb-seq:** Marson-lab genome-wide CRISPRi screen, primary human CD4+ T cells.
  Repo `emdann/GWT_perturbseq_analysis_2025`, `metadata/suppl_tables/DE_stats.suppl_table.csv`
  and `metadata/gene_lists/*.tsv`.
- **Breast-cancer network:** Kim et al., "A protein interaction landscape of breast cancer,"
  *Science* 374, eabf3066 (2021). 40 baits ± mutation across MCF7 / MDA-MB-231 / MCF10A;
  589 high-confidence PPIs; networks substantially rewired by mutation.
- **Dynamics thesis:** FeatureDock (physicochemical-feature docking) + Dyna-1 (µs–ms
  flexibility prediction), this hackathon project.
