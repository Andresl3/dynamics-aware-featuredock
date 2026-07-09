"""
precompute_dyna1.py  --  batch Dyna-1 (ESM-2) inference, model loaded ONCE.

The stock dyna1-esm2.py reloads the 205 MB model on every call. In the
preprocessing loop that fixed cost is paid ~5,300 times and dominates runtime.
This script loads the model + tokenizer a single time, then loops over all
protein structures, writing one <pid>.csv (columns: position,residue,p_exchange)
per structure -- byte-compatible with what dyna1-esm2.py produces, so the
downstream featurize_dyna1_channel.py reads them unchanged.

Run this ONCE before the §8 preprocessing loop. §8 then just reads the cached
CSV (instant) instead of spawning a subprocess per structure.

Usage:
    python precompute_dyna1.py \
        --pdbbind-dir /content/pdbbind/P-L \
        --refined-list /content/featuredock/data/pdblist.txt \
        --save-dir /content/drive/MyDrive/Dynamics_aware_featuredock/dyna1_csv

Resumable: structures whose CSV already exists are skipped.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, argparse, re
import numpy as np
import pandas as pd
import torch

# --- Dyna-1 imports (run from the Dyna-1 repo root, or pass --dyna1-root) ---
def _import_dyna1(dyna1_root):
    sys.path.insert(0, dyna1_root)
    global utils, ESM_model
    import utils as _utils
    from model.model import ESM_model as _ESM_model
    utils = _utils
    ESM_model = _ESM_model

# --- sequence extraction: SAME logic as §8 (uppercase 3->1, non-canonical -> G) ---
from Bio.PDB import PDBParser
from Bio.PDB.Polypeptide import is_aa
from Bio.Data.PDBData import protein_letters_3to1_extended as _T2O
T2O_UP = {k.upper(): v for k, v in _T2O.items()}
VALID = set("ACDEFGHIKLMNPQRSTVWY")

def extract_seq(pdb_path, chain=None):
    model = next(PDBParser(QUIET=True).get_structure('s', pdb_path).get_models())
    seq = []
    for ch in model:
        if chain and ch.id != chain: continue
        for res in ch:
            if is_aa(res, standard=True) and not res.id[0].strip():
                seq.append(T2O_UP.get(res.resname.strip().upper(), 'G'))
    return ''.join(seq)

_VALID_RE = re.compile('^[acdefghiklmnpqrstvwy]*$', re.I)

def find_complex_dirs(root):
    """Yield (pid, dir) for flat OR nested P-L/<year>/<pid> layouts."""
    for a in sorted(os.listdir(root)):
        ad = os.path.join(root, a)
        if not os.path.isdir(ad): continue
        if os.path.exists(os.path.join(ad, f'{a}_protein.pdb')):
            yield a, ad
        else:
            for b in sorted(os.listdir(ad)):
                bd = os.path.join(ad, b)
                if os.path.isdir(bd) and os.path.exists(os.path.join(bd, f'{b}_protein.pdb')):
                    yield b, bd

def main(args):
    _import_dyna1(args.dyna1_root)
    os.makedirs(args.save_dir, exist_ok=True)
    DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[precompute] device = {DEVICE}")

    # --- load model + tokenizer ONCE ---
    from transformers import AutoTokenizer
    model = ESM_model(method='esm2', nheads=8, nlayers=12, layer=30).to(DEVICE)
    wpath = os.path.join(args.dyna1_root, 'model/weights/dyna1-esm2.pt')
    model.load_state_dict(torch.load(wpath, map_location=DEVICE), strict=False)
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained("facebook/esm2_t6_8M_UR50D")
    print("[precompute] model + tokenizer loaded once")

    # --- build the structure list (refined subset if a list is given) ---
    refined = None
    if args.refined_list and os.path.exists(args.refined_list):
        refined = {l.strip().lower() for l in open(args.refined_list) if l.strip()}
        print(f"[precompute] filtering to {len(refined)} refined ids")
    todo = []
    for pid, cdir in find_complex_dirs(args.pdbbind_dir):
        if refined is not None and pid.lower() not in refined: continue
        todo.append((pid, os.path.join(cdir, f'{pid}_protein.pdb')))
    print(f"[precompute] {len(todo)} structures to consider")

    ok = skip = bad = 0
    from tqdm.auto import tqdm
    for pid, prot in tqdm(todo):
        out_csv = os.path.join(args.save_dir, f'{pid}.csv')
        if os.path.exists(out_csv) and not args.overwrite:
            skip += 1; continue
        try:
            seq = extract_seq(prot)
            if not seq or _VALID_RE.search(seq) is None:
                bad += 1; continue
            seq_input = tokenizer.encode(seq, add_special_tokens=False, return_tensors='pt').to(DEVICE)
            sequence_id = seq_input != 1
            with torch.no_grad():
                logits = model(seq_input, sequence_id)
            p = utils.prob_adjusted(logits).cpu().detach().numpy().squeeze()
            pd.DataFrame({'position': np.arange(1, len(p)+1),
                          'residue': np.array(list(seq)),
                          'p_exchange': p}).to_csv(out_csv, index=False)
            ok += 1
        except Exception as e:
            bad += 1
            print(f"  {pid}: {type(e).__name__}: {str(e)[:120]}")
    print(f"\n[precompute] done: {ok} written, {skip} skipped(existing), {bad} failed")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdbbind-dir', required=True, help='root of PDBBind (flat or P-L/year/pid)')
    ap.add_argument('--refined-list', default=None, help='pdblist.txt of refined ids (optional filter)')
    ap.add_argument('--save-dir', required=True, help='where to write <pid>.csv')
    ap.add_argument('--dyna1-root', default='/content/Dyna-1', help='Dyna-1 repo root')
    ap.add_argument('--overwrite', action='store_true')
    main(ap.parse_args())
