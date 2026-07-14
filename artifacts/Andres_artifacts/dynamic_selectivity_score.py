#!/usr/bin/env python3
"""
dynamic_selectivity_score.py
============================
A NO-RETRAINING scoring layer on top of Dyna-1 p_exchange predictions.

Question it answers
-------------------
Given a drug whose binding site on a TARGET protein is known (a crystal pose
or a docked pose), does the drug engage residues that undergo slow (us-ms)
conformational exchange in the TARGET but NOT in a chosen OFF-TARGET?
If yes, the drug has a route to *dynamic selectivity* -- selectivity that is
invisible to a static structure (the Abl/Src imatinib paradox).

It consumes Dyna-1 per-residue p_exchange (position, residue, p_exchange) and a
list of binding-site residues. It does NOT touch FeatureDock and requires no
training. It is a read-out layer.

Design decisions grounded in this dataset (see caveats)
-------------------------------------------------------
1. READ THE ACCESSIBLE (APO / UNLIGANDED) STATE.  On imatinib-bound Abl (3PYY)
   and Src (2OIQ) the pocket p_exchange is flat (0.461 vs 0.471, no residue
   > 0.6): the bound pocket is dynamically quenched. Selectivity lives in the
   slow motion of the *accessible* state that the drug must capture, so run
   Dyna-1 on the apo / unliganded structure (or an AF2 model), not the holo.
2. USE A POCKET-LEVEL CONTRAST, NOT A SINGLE RESIDUE.  Per-residue p_exchange
   correlates only weakly with any single structural feature; the usable signal
   is the aggregate over the footprint (RelaxDB per-residue analysis).
3. NORMALISE TO THE WHOLE-PROTEIN BACKGROUND.  Globally floppy proteins have
   high p_exchange everywhere; enrichment = footprint_mean - protein_mean
   isolates pocket-specific exchange.

Score
-----
For one protein/state:
    footprint_mean  = mean p_exchange over binding-site residues
    enrichment      = footprint_mean - whole_protein_mean
    frac_hi         = fraction of footprint residues with p_exchange >= HI (0.5)
    peak            = max p_exchange in footprint

Dynamic-Selectivity Score between a target and an off-target (same/analogous
drug footprint mapped onto each):
    DSS_mean = footprint_mean(target)  - footprint_mean(offtarget)
    DSS_enr  = enrichment(target)      - enrichment(offtarget)
    DSS_hi   = frac_hi(target)         - frac_hi(offtarget)
A positive DSS says the drug's footprint is more dynamic on the target than on
the off-target -> the target offers a slow-motion state the drug can select for
that the off-target does not. Report all three; they should agree in sign for a
robust call.

Usage
-----
    from dynamic_selectivity_score import footprint_score, dynamic_selectivity
    t = footprint_score("apo_target.csv", target_pocket_resids)
    o = footprint_score("apo_offtarget.csv", offtarget_pocket_resids)
    print(dynamic_selectivity(t, o))

CSV format: columns position,residue,p_exchange  (Dyna-1 output, 1..N).
Pocket resids are given in the SAME numbering as the CSV 'position' column.
"""
import numpy as np, pandas as pd

HI = 0.5  # p_exchange threshold for "in slow exchange"

def load_pex(csv):
    d = pd.read_csv(csv)
    return {int(p): float(v) for p, v in zip(d.position, d.p_exchange)}

def footprint_score(csv, pocket_resids):
    """Score one protein state. pocket_resids indexed to CSV 'position'."""
    pex = load_pex(csv)
    vals = [pex[r] for r in pocket_resids if r in pex]
    if not vals:
        raise ValueError("no pocket residues found in CSV numbering")
    allv = list(pex.values())
    return {
        "n_footprint": len(vals),
        "footprint_mean": float(np.mean(vals)),
        "protein_mean": float(np.mean(allv)),
        "enrichment": float(np.mean(vals) - np.mean(allv)),
        "frac_hi": float(np.mean([v >= HI for v in vals])),
        "peak": float(np.max(vals)),
    }

def dynamic_selectivity(target, offtarget):
    """Contrast two footprint_score dicts (target vs off-target)."""
    dss = {
        "DSS_mean": target["footprint_mean"] - offtarget["footprint_mean"],
        "DSS_enrichment": target["enrichment"] - offtarget["enrichment"],
        "DSS_frac_hi": target["frac_hi"] - offtarget["frac_hi"],
    }
    signs = np.sign([dss["DSS_mean"], dss["DSS_enrichment"], dss["DSS_frac_hi"]])
    dss["agree"] = bool(abs(signs.sum()) == 3)
    dss["call"] = ("dynamic-selective for TARGET" if dss["DSS_enrichment"] > 0.03
                   else "dynamic-selective for OFF-TARGET" if dss["DSS_enrichment"] < -0.03
                   else "no dynamic selectivity (flat)")
    return dss

if __name__ == "__main__":
    import sys, json
    # demo call signature: script target.csv "1,2,3" offtarget.csv "4,5,6"
    if len(sys.argv) == 5:
        tp = [int(x) for x in sys.argv[2].split(",")]
        op = [int(x) for x in sys.argv[4].split(",")]
        t = footprint_score(sys.argv[1], tp)
        o = footprint_score(sys.argv[3], op)
        print(json.dumps({"target": t, "offtarget": o,
                          "selectivity": dynamic_selectivity(t, o)}, indent=2))
    else:
        print(__doc__)
