#!/usr/bin/env python
"""
preprocess.py -- Dynamics-aware FeatureDock preprocessing, headless / HPC version.

Standalone command-line equivalent of the Colab notebook's section 8. For every
PDBBind complex it runs the 6-stage pipeline:

    1. prepare_structure.py          -> cleaned apo protein (+DSSP) and ligand
    2. create_voxels_and_landmarks   -> pocket grid + landmarks  (PATCHED loaders)
    3. featurize.py                  -> native FEATURE (N,480)  -> OUT80
    4. dyna1 p_exchange              -> per-residue motion CSV   (cached, reused)
    5. featurize_dyna1_channel.py    -> append motion (N,486)    -> OUT81
    6. label_voxels.py               -> occupancy labels (both widths)

Resumable: complexes whose (OUT81/<pid>.property.pvar + labels) already exist
are skipped. Dyna-1 CSVs are cached in --out-dir/dyna1_csv and reused across runs.

Example (SLURM job body):
    python preprocess.py \
        --pdbbind-dir  $DATA/PDBbind_v2020/P-L \
        --featuredock  $HOME/dynamics-aware-featuredock/featuredock \
        --dyna1-root   $HOME/dynamics-aware-featuredock/Dyna-1 \
        --out-dir      $SCRATCH/dyna_featuredock_out \
        --refined-only

Set --shard K/N to split the work across N array tasks (see run_preprocess.slurm).
"""
import os, sys, argparse, subprocess, json, re
from collections import Counter

# ---------------- CLI ----------------
def get_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdbbind-dir', required=True,
                    help='PDBBind root; flat <pid>/ or nested P-L/<year>/<pid>/')
    ap.add_argument('--featuredock', required=True, help='path to featuredock repo')
    ap.add_argument('--dyna1-root',  required=True, help='path to Dyna-1 repo')
    ap.add_argument('--out-dir',     required=True, help='output root (use scratch)')
    ap.add_argument('--refined-only', action='store_true',
                    help='keep only ids in featuredock/data/pdblist.txt')
    ap.add_argument('--shard', default='1/1',
                    help='K/N: process the K-th of N equal shards (for job arrays)')
    ap.add_argument('--limit', type=int, default=0, help='cap #structures (smoke test)')
    ap.add_argument('--timeout', type=int, default=1800, help='per-subprocess timeout (s)')
    return ap.parse_args()

# ---------------- sequence extraction (uppercase 3->1; non-canonical -> G) -------------
from Bio.PDB import PDBParser
from Bio.PDB.Polypeptide import is_aa
from Bio.Data.PDBData import protein_letters_3to1_extended as _T2O
T2O_UP = {k.upper(): v for k, v in _T2O.items()}
_VALID_RE = re.compile('^[acdefghiklmnpqrstvwy]*$', re.I)

def extract_seq(pdb_path, chain=None):
    m = next(PDBParser(QUIET=True).get_structure('s', pdb_path).get_models())
    seq = []
    for ch in m:
        if chain and ch.id != chain:
            continue
        for res in ch:
            if is_aa(res, standard=True) and not res.id[0].strip():
                seq.append(T2O_UP.get(res.resname.strip().upper(), 'G'))
    return ''.join(seq)

# ---------------- discovery (flat OR nested layout) ----------------
def find_complex_dirs(root):
    for a in sorted(os.listdir(root)):
        ad = os.path.join(root, a)
        if not os.path.isdir(ad):
            continue
        if os.path.exists(os.path.join(ad, f'{a}_protein.pdb')):
            yield a, ad
        else:
            for b in sorted(os.listdir(ad)):
                bd = os.path.join(ad, b)
                if os.path.isdir(bd) and os.path.exists(os.path.join(bd, f'{b}_protein.pdb')):
                    yield b, bd

def main():
    args = get_args()
    FD, DY = args.featuredock, args.dyna1_root
    SCRIPTS = f'{FD}/src/curate_dataset'
    FEATURE_PROGRAM = f'{FD}/src/feature-3.1.0'
    DSSP = f'{FD}/src/utils/dssp'

    O = args.out_dir
    APO, HET, VOX, FFD, DET = (f'{O}/apo', f'{O}/het', f'{O}/voxels', f'{O}/ff', f'{O}/voxel_details')
    DY_CSV, OUT80, OUT81 = f'{O}/dyna1_csv', f'{O}/pvar_80', f'{O}/pvar_81'
    for d in (APO, HET, VOX, FFD, DET, DY_CSV, OUT80, OUT81):
        os.makedirs(d, exist_ok=True)

    def sh(cmd, cwd=None):
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True,
                           text=True, timeout=args.timeout)
        return r.returncode, r.stdout, r.stderr

    def process_one(pid, prot_pdb, lig_sdf):
        sh(f'python {SCRIPTS}/prepare_structure.py --pdbid={pid} '
           f'--protfile={prot_pdb} --ligfile={lig_sdf} '
           f'--apodir={APO} --hetdir={HET} --dssp={DSSP} --rm_all_het')
        apo = f'{APO}/{pid}.pdb'; het = f'{HET}/{pid}_ligand.sdf'
        if not os.path.exists(apo):
            return 'prepare_failed'
        sh(f'python {SCRIPTS}/create_voxels_and_landmarks.py --pdbid={pid} '
           f'--apofile={apo} --hetfile={het} --outdir={DET} '
           f'--pocket_cutoff=6.0 --spacing=1.0 --trim --trim_min=1.0 --trim_max=6.0 '
           f'--abs_include --heavyatom --intermediate --overwrite')
        for suf in ('voxels.pkl', 'landmarks.pkl'):
            s = f'{DET}/{pid}.{suf}'
            if os.path.exists(s):
                sh(f'mv {s} {VOX}/')
        vox = f'{VOX}/{pid}.voxels.pkl'
        if not os.path.exists(vox):
            return 'voxels_failed'
        sh(f'python {SCRIPTS}/featurize.py --pdbid={pid} --voxelfile={vox} '
           f'--voxeldir={OUT80} --tempdir={FFD} --searchdir={APO} '
           f'--featurize={FEATURE_PROGRAM} --numshell=6 --width=1.25 --overwrite')
        pvar80 = f'{OUT80}/{pid}.property.pvar'
        if not os.path.exists(pvar80):
            return 'featurize_failed'
        # Dyna-1: reuse cached CSV if present, else generate via the stock script
        csv = f'{DY_CSV}/{pid}.csv'
        if not os.path.exists(csv):
            seq = extract_seq(apo)
            if not seq or _VALID_RE.search(seq) is None:
                return 'bad_seq'
            sh(f'python dyna1-esm2.py --sequence {seq} --name {pid} --save_dir {DY_CSV}', cwd=DY)
        if not os.path.exists(csv):
            return 'dyna1_failed'
        sh(f'python {SCRIPTS}/featurize_dyna1_channel.py --pdb {apo} --voxelfile {vox} '
           f'--pvarfile {pvar80} --dyna1csv {csv} --out {OUT81}/{pid}.property.pvar')
        if not os.path.exists(f'{OUT81}/{pid}.property.pvar'):
            return 'channel_failed'
        lm = f'{VOX}/{pid}.landmarks.pkl'
        sh(f'python {SCRIPTS}/label_voxels.py --pdbid={pid} --voxelfile={vox} --lmfile={lm} '
           f'--configfile={SCRIPTS}/label_config.json --hard --outdir={OUT80} '
           f'--interactions HeavyAtomsite --overwrite')
        lab = f'{OUT80}/{pid}.HeavyAtomsite.labels.pkl'
        if not os.path.exists(lab):
            return 'label_failed'
        sh(f'cp {lab} {OUT81}/')
        return 'ok'

    # build the work list
    refined = None
    if args.refined_only:
        rl = f'{FD}/data/pdblist.txt'
        refined = {l.strip().lower() for l in open(rl) if l.strip()}
    todo = []
    for pid, cdir in find_complex_dirs(args.pdbbind_dir):
        if refined is not None and pid.lower() not in refined:
            continue
        prot = os.path.join(cdir, f'{pid}_protein.pdb')
        lig = os.path.join(cdir, f'{pid}_ligand.sdf')
        if os.path.exists(prot) and os.path.exists(lig):
            todo.append((pid, prot, lig))

    # shard for job arrays: K/N
    k, n = (int(x) for x in args.shard.split('/'))
    todo = todo[(k - 1)::n]
    if args.limit:
        todo = todo[:args.limit]
    print(f'[preprocess] shard {k}/{n}: {len(todo)} complexes', flush=True)

    log = {}
    for i, (pid, prot, lig) in enumerate(todo, 1):
        if (os.path.exists(f'{OUT81}/{pid}.property.pvar')
                and os.path.exists(f'{OUT81}/{pid}.HeavyAtomsite.labels.pkl')):
            log[pid] = 'skip(done)'
        else:
            try:
                log[pid] = process_one(pid, prot, lig)
            except Exception as ex:
                log[pid] = f'exception: {str(ex)[:80]}'
        if i % 50 == 0:
            print(f'  {i}/{len(todo)}  {Counter(v.split(":")[0] for v in log.values())}', flush=True)

    ok = sum(1 for v in log.values() if v in ('ok', 'skip(done)'))
    print(f'\n[preprocess] DONE shard {k}/{n}: {ok}/{len(todo)} ok', flush=True)
    print('[preprocess] outcomes:', Counter(v.split(':')[0] for v in log.values()), flush=True)
    logpath = f'{O}/preprocess_log_shard{k}of{n}.json'
    json.dump(log, open(logpath, 'w'), indent=2)
    print('[preprocess] log ->', logpath, flush=True)

if __name__ == '__main__':
    main()
