import warnings
warnings.filterwarnings("ignore")
import re
import utils
import torch
import random
import argparse
import numpy as np
import pandas as pd

from model.model import *
from transformers import AutoTokenizer

warnings.filterwarnings("ignore")
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def handle_name(args):
    """Processes the output file name given inputs of args.name; otherwise generates a random number"""
    if args.name:
        return args.name
    else:
        name = random.randint(0, 100000)
    return f'{name}-Dyna1_ESM2'

def main(args):

    output_base = handle_name(args)
    
    model = ESM_model(method='esm2', nheads=8, nlayers=12, layer=30).to(DEVICE)
    model.load_state_dict(torch.load('model/weights/dyna1-esm2.pt', map_location=DEVICE), strict=False)
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(f"facebook/esm2_t6_8M_UR50D")
    seq_input = tokenizer.encode(args.sequence, add_special_tokens=False, return_tensors='pt').to(DEVICE)
    sequence_id = seq_input != 1
    logits = model(seq_input, sequence_id)
    seq_len = len(args.sequence)
    p = utils.prob_adjusted(logits).cpu().detach().numpy().squeeze()
    out_df = pd.DataFrame({'position': np.arange(1,len(p)+1), 'residue': np.array(list(args.sequence)), 'p_exchange': p,})
    out_df.to_csv(os.path.join(args.save_dir, f'{output_base}.csv'), index=False)

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Example script with integer and string arguments')
    parser.add_argument('--sequence', type=str, required=True)
    parser.add_argument('--name', type=str)
    parser.add_argument('--save_dir', type=str, default = '.')
    args = parser.parse_args()
    
    alphabets = {'protein': re.compile('^[acdefghiklmnpqrstvwy]*$', re.I)}
    if alphabets['protein'].search(args.sequence) is None:
         exit('Invalid sequence given.')

    main(args)


