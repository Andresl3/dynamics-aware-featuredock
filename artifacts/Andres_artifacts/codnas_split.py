#!/usr/bin/env python3
"""
Leakage-free 90%-identity cluster split of the CoDNaS conformational-diversity DB.

Same protocol as the FeatureDock/Dyna-1 MMseqs2 cluster split used elsewhere in
this project: cluster representative sequences at 90% identity, then assign each
WHOLE cluster to exactly one of train/val/test so that no 90%-identity cluster
spans two splits (this is what prevents homolog leakage).

Usage
-----
    # 1. sequences already in a FASTA (id -> sequence):
    python codnas_split.py --fasta codnas_seqs.fasta --out .

    # 2. sequences in a CSV with columns ID,sequence:
    python codnas_split.py --csv codnas_seqs.csv --out .

Outputs: train.csv, val.csv, test.csv  (columns: ID,sequence),
         plus codnas_clusters.tsv (cluster assignments) and split_summary.json.

Split ratio 80/10/10 by CLUSTER, fixed seed 42.
"""
import argparse, subprocess, os, sys, json, random, csv, shutil

MIN_SEQ_ID = 0.9      # 90% identity
COVERAGE   = 0.8      # -c 0.8
SEED       = 42
RATIOS     = (0.80, 0.10, 0.10)   # train, val, test

def read_fasta(path):
    seqs={}; cur=None; buf=[]
    with open(path) as fh:
        for line in fh:
            line=line.rstrip()
            if not line: continue
            if line.startswith(">"):
                if cur is not None: seqs[cur]="".join(buf)
                cur=line[1:].split()[0]; buf=[]
            else:
                buf.append(line)
    if cur is not None: seqs[cur]="".join(buf)
    return seqs

def read_csv_seqs(path):
    seqs={}
    with open(path, newline="") as fh:
        r=csv.DictReader(fh)
        # tolerate ID/id and sequence/seq column names
        idc=[c for c in r.fieldnames if c.lower() in ("id","pdb","name")][0]
        sc=[c for c in r.fieldnames if c.lower() in ("sequence","seq")][0]
        for row in r:
            i=row[idc].strip(); s=row[sc].strip().upper()
            if i and s: seqs[i]=s
    return seqs

def write_fasta(seqs, path):
    with open(path,"w") as fh:
        for i,s in seqs.items():
            fh.write(f">{i}\n{s}\n")

def run_mmseqs(fasta, workdir):
    """mmseqs easy-cluster fasta clust tmp --min-seq-id 0.9 -c 0.8 -> clust_cluster.tsv"""
    os.makedirs(workdir, exist_ok=True)
    pref=os.path.join(workdir,"clust")
    tmp=os.path.join(workdir,"tmp")
    cmd=["mmseqs","easy-cluster",fasta,pref,tmp,
         "--min-seq-id",str(MIN_SEQ_ID),"-c",str(COVERAGE)]
    print("[mmseqs]"," ".join(cmd)); subprocess.run(cmd, check=True)
    return pref+"_cluster.tsv"   # 2 cols: representative<TAB>member

def assign_splits(cluster_tsv, seqs):
    # map representative -> [members]
    clusters={}
    with open(cluster_tsv) as fh:
        for line in fh:
            rep,mem=line.rstrip("\n").split("\t")
            clusters.setdefault(rep,[]).append(mem)
    reps=sorted(clusters)                     # deterministic order
    rng=random.Random(SEED); rng.shuffle(reps)
    n=len(reps); n_tr=int(n*RATIOS[0]); n_va=int(n*RATIOS[1])
    split_of={}
    for k,rep in enumerate(reps):
        split = "train" if k<n_tr else ("val" if k<n_tr+n_va else "test")
        for mem in clusters[rep]:
            split_of[mem]=split
    return clusters, split_of

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fasta"); ap.add_argument("--csv"); ap.add_argument("--out",default=".")
    ap.add_argument("--workdir",default="mmseqs_work")
    a=ap.parse_args()
    if a.fasta: seqs=read_fasta(a.fasta)
    elif a.csv: seqs=read_csv_seqs(a.csv)
    else: sys.exit("provide --fasta or --csv")
    print(f"[load] {len(seqs)} sequences")
    os.makedirs(a.out, exist_ok=True)
    fa=os.path.join(a.out,"codnas_seqs.fasta"); write_fasta(seqs, fa)
    ctsv=run_mmseqs(fa, a.workdir)
    clusters, split_of = assign_splits(ctsv, seqs)
    # write per-split CSVs
    counts={"train":0,"val":0,"test":0}
    handles={s:open(os.path.join(a.out,f"{s}.csv"),"w",newline="") for s in counts}
    writers={s:csv.writer(handles[s]) for s in counts}
    for w in writers.values(): w.writerow(["ID","sequence"])
    for i,s in seqs.items():
        sp=split_of.get(i)
        if sp is None: continue
        writers[sp].writerow([i,s]); counts[sp]+=1
    for h in handles.values(): h.close()
    # cluster table
    with open(os.path.join(a.out,"codnas_clusters.tsv"),"w") as fh:
        fh.write("member\trepresentative\tsplit\n")
        for rep,mems in clusters.items():
            for m in mems: fh.write(f"{m}\t{rep}\t{split_of[m]}\n")
    summary={"n_sequences":len(seqs),"n_clusters":len(clusters),
             "min_seq_id":MIN_SEQ_ID,"coverage":COVERAGE,"seed":SEED,
             "ratios":{"train":RATIOS[0],"val":RATIOS[1],"test":RATIOS[2]},
             "counts":counts,
             "cluster_sizes":{"min":min(len(m) for m in clusters.values()),
                              "max":max(len(m) for m in clusters.values()),
                              "mean":round(sum(len(m) for m in clusters.values())/len(clusters),2)}}
    json.dump(summary, open(os.path.join(a.out,"split_summary.json"),"w"), indent=2)
    print(json.dumps(summary, indent=2))

if __name__=="__main__":
    main()
