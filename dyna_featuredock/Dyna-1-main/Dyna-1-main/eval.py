import warnings
warnings.filterwarnings("ignore")

import argparse
import torch
import random
import numpy as np
import pandas as pd
import numpy as np

from torch.utils.data.dataloader import DataLoader
from torchmetrics import PrecisionRecallCurve

import utils
from model.model import *
from data.dataloader import DynaData

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def load_weights(args):

    if 'esm' in args.method:
        output_base = f'{args.input}_{args.method}'
        fp = os.path.join(args.weights_dir, f'layer{args.layer}.pt')
        weights = torch.load(fp)
    elif 'af2' in args.method:
        output_base = f'{args.input}_{args.method}'
        fp = os.path.join(args.weights_dir, f'af2.pt')
        weights = torch.load(fp)
    elif 'baseline' in args.method:
        output_base = f'{args.input}_{args.method}'
        fp = os.path.join(args.weights_dir, f'baseline.pt')
        weights = torch.load(fp)
    else:
        exit('Invalid model passed.') 

    if args.layer != -1:
        output_base = f'{output_base}_layer{args.layer}'
    if args.missing_only or args.rex_only or args.unsuppressed:
        output_base = f'{output_base}_'
        if args.missing_only:
            output_base = f'{output_base}M'
        if args.rex_only:
            output_base = f'{output_base}R'
        if args.unsuppressed:
            output_base = f'{output_base}Y'

    return weights, output_base, fp

def get_probs(method, model, dataloader):
    
    outs = []
    
    for _, batch in enumerate(dataloader):
        with torch.no_grad():

            targets = batch['targets'].to(DEVICE)
            eval_mask = batch['eval_mask'].to(DEVICE)
            names = batch['names']
            seq_id =  batch['seq_id'].to(DEVICE,non_blocking=True)

            if 'esm3' in method:
                seq_input, struct_input = None, None
                if args.seq:
                    seq_input = batch['seqs'].to(DEVICE,non_blocking=True)
                if args.struct:
                    struct_input = batch['structs'].to(DEVICE)
                logits = model((seq_input, struct_input), seq_id)
            elif 'esm2' in method:
                seq_input = batch['seqs'].to(DEVICE,non_blocking=True)
                logits = model(seq_input, seq_id)
            elif 'af2' in method:
                pair_reps = batch['pair_reps'].to(DEVICE,non_blocking=True).to(torch.float32)
                logits = model(pair_reps, seq_id) 
            elif 'baseline' in method:
                seq_input = batch['seqs'].to(DEVICE,non_blocking=True)
                logits = model(seq_input, seq_id)        
            
            torch_sig = torch.sigmoid(logits)
            p = utils.prob_adjusted(logits)
            outs.append({'entry_ID': str(names[0]),
                          'torch_sig': torch_sig.detach().cpu().numpy(),
                          'p': p.detach().cpu().numpy(),
                          'logits': logits.detach().cpu().numpy(),
                          'target': targets[0].detach().cpu().numpy(),
                          'eval_mask': eval_mask[0].detach().cpu().numpy()})

    return pd.DataFrame.from_records(outs)

def get_metrics(row, t):
    logits, labels, mask = row['p'], row['target'], row['eval_mask']
    masked_logits, masked_labels = utils.get_masked(logits, labels, mask)
    auroc, auprc, auprc_norm = utils.get_auroc(masked_logits, masked_labels)
    
    return utils.get_pr_metrics(masked_logits, masked_labels, t) + (auroc.item(), auprc.item(), auprc_norm.item())

def get_thresholds(probs_df):

    logits = torch.tensor(probs_df['p'])
    mask = torch.tensor(probs_df['eval_mask'])
    labels = torch.tensor(probs_df['target'])
    
    masked_logits, masked_labels = utils.get_masked(logits, labels, mask)
    
    pr_curve = PrecisionRecallCurve(task="binary")
    precision, recall, thresholds = pr_curve(masked_logits, masked_labels.int())

    optimal_idx = torch.argmax(2*precision * recall / (precision+recall + 1e-8)).item()
    t = thresholds[optimal_idx].item()
    return t

def main(args):
    which_method = args.method.split('_')[0]
    config, config_dict = utils.load_config(f'configs/{which_method}.yml', return_dict=True)
    weights, output_base, fp = load_weights(args)
    if args.save_dir is not None:
        config.dir.save_dir = args.save_dir
    
    if 'esm' in args.method:
        model = ESM_model(which_method, 
                          nlayers = config.model.nlayers,
                          nheads = config.model.nheads,
                          layer = args.layer).to(DEVICE)
    elif 'af2' in args.method:
        model = AF2_model(res_count = config.model.res_count, 
                          hidden_size = config.model.hidden_size,
                          length = config.model.length,
                          nlayers = config.model.nlayers,
                          nheads = config.model.nheads,
                          dropout = config.train.dropout).to(DEVICE,non_blocking=True).to(torch.float32)
    elif 'baseline' in args.method:
        model = BaselineOHE(nlayers = config.model.nlayers,
                            nheads = config.model.nheads,
                            dropout = config.train.dropout).to(DEVICE,non_blocking=True)
    if 'model_state_dict' in weights.keys():
        from collections import OrderedDict
        temp = OrderedDict()
        for k, value in weights["model_state_dict"].items():
            if 'classifier' in k:
                temp[k] = value
        torch.save(temp, fp)
        model.load_state_dict(temp, strict=False)
        print('saved!!')
    else:
        model.load_state_dict(weights, strict=False)
    model.eval()
    
    dataset = DynaData(config_dict['data'][args.input]['split'],
                      type = config_dict['data'][args.input]['type'],
                      crop_len = config_dict['data'][args.input]['crop_len'], 
                      cluster_file = config.data.cluster,
                      missing_only = args.missing_only,
                      rex_only = args.rex_only, 
                      pair_rep = config.data.pair_rep,
                      unsuppressed = args.unsuppressed,
                      method = (args.method, model))

    loader = DataLoader(dataset = dataset, 
                            batch_size = 1, 
                            shuffle = False, 
                            drop_last = False,
                            collate_fn = dataset.__collate_fn__)

    probs_df = get_probs(args.method, model, loader)
    t = get_thresholds(probs_df)
    cols = ['F1','precision','recall', 'n_tot', 'n_pos', 'AUROC', 'AUPRC', 'AUPRC_norm']
    
    probs_df[cols] = probs_df.apply(lambda row: get_metrics(row, t), axis=1, result_type='expand')
    path = os.path.join(f'{config.dir.save_dir}', f'{output_base}.json.zip')
    probs_df.to_json(path)

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Example script with integer and string arguments')
    parser.add_argument('input', type=str)
    parser.add_argument('--method', type=str, required=True)
    parser.add_argument('--weights_dir', type=str, required=True)
    parser.add_argument('--layer', type=int)

    parser.add_argument('--rex_only', action='store_true')
    parser.add_argument('--missing_only', action='store_true')
    parser.add_argument('--unsuppressed', action='store_true')

    parser.add_argument('--seq', action='store_true')
    parser.add_argument('--struct', action='store_true')
    parser.add_argument('--save_dir', type=str, default = None)

    args = parser.parse_args()

    if 'relax' not in args.input and 'cpmg' not in args.input and args.rex_only:
        exit('Only RelaxDB and CPMG datasets accept the rex argument. Exiting now...')
    if 'cpmg' not in args.input and args.unsuppressed:
        exit('Only CPMG dataset accepts unsuppressed argument. Exiting now...')
    if args.missing_only and args.unsuppressed:
        exit('To evaluate on unsuppressed, you must also evaluate on rex. Exiting now...')
    if 'esm3' in args.method and (args.layer < 0 or args.layer > 47):
        exit('ESM3 only has 48 layers, accepted values are [0-47]')
    if args.method == 'esm2' and (args.layer < 0 or args.layer > 30):
        exit('ESM2 only has 31 layers, accepted values are [0-30]')
    main(args)


