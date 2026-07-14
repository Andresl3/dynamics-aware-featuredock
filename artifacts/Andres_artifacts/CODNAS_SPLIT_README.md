# Leakage-free 90%-identity cluster split of CoDNaS

`codnas_split.py` builds a homolog-leakage-free train/val/test split of the CoDNaS
conformational-diversity database, using the **same MMseqs2 90%-identity
cluster-split protocol** used for the FeatureDock/Dyna-1 data elsewhere in this
project.

## What it does
1. Reads CoDNaS representative sequences (FASTA or `ID,sequence` CSV).
2. `mmseqs easy-cluster seqs.fasta clust tmp --min-seq-id 0.9 -c 0.8` → clusters
   at 90% identity, 80% coverage.
3. Shuffles **clusters** (seed 42) and assigns each WHOLE cluster to exactly one
   of train/val/test at 80/10/10. Because assignment is by cluster, **no
   90%-identity cluster can span two splits** — that is what removes homolog
   leakage. Every member inherits its representative's split.
4. Writes `train.csv` / `val.csv` / `test.csv` (columns `ID,sequence`), plus
   `codnas_clusters.tsv` (member→representative→split) and `split_summary.json`.

## Status of this run
- **Pipeline: built and VERIFIED.** On a 75-sequence synthetic test (60 base
  sequences + 15 deliberately near-identical variants), MMseqs2 collapsed the
  variants into their base clusters (75→60 clusters) and the split passed all
  three leakage assertions:
  - 0 clusters spanning more than one split
  - 0 near-duplicate pairs separated across splits
  - 0 IDs appearing in more than one CSV; all 75 accounted for.
- **CoDNaS sequences: NOT yet downloaded.** `codnas.unq.edu.ar` was allowlisted
  on request, but the server returned a persistent HTTP **503 Service
  Unavailable** on every path and retry — an outage on their side, not a sandbox
  block. The real split could not be produced without the input sequences.

## To produce the real split (one command once inputs exist)
```bash
conda activate mmseqs          # env already created (mmseqs2 v18.8cc5c)
python codnas_split.py --fasta codnas_seqs.fasta --out codnas_split
# or, if you have a CSV:
python codnas_split.py --csv codnas_seqs.csv --out codnas_split
```
Get the sequences by either:
- **retrying CoDNaS** when the server is back (`https://codnas.unq.edu.ar/` →
  its download / API endpoint for representative sequences), or
- **supplying a local dump** — any FASTA, or a CSV with `ID,sequence` columns.
  If you have only a PDB accession list, I can fetch the sequences from RCSB
  (which IS reachable here) and assemble the FASTA.

Parameters (top of `codnas_split.py`): `MIN_SEQ_ID=0.9`, `COVERAGE=0.8`,
`SEED=42`, `RATIOS=(0.80,0.10,0.10)`.
