import os
import gc
import torch
import utils
import argparse
import numpy as np
import pandas as pd
from torch.utils.data.dataloader import DataLoader

from model import *
from data.dataloader import DynaData

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def get_data(dataloader):
    outs = []
    df_aa = pd.read_csv('data/probs/probs_aa.csv', index_col=0, 
                dtype={"token": int, "target": float}).to_dict()['target']
    df_dssp = pd.read_csv('data/probs/probs_dssp.csv', index_col=0,
                dtype={"dssp": float, "target": float}).to_dict()['target']
    df_aa_dssp = pd.read_csv('data/probs/probs_aa_dssp.csv', 
                dtype={"dssp": float, "token": int, "target": float})

    for _, batch in enumerate(dataloader):
        
        names = batch['names']
        target = batch['targets'].detach().cpu().numpy()
        eval_mask = batch['eval_mask'].bool().detach().cpu().numpy()
        dssp = batch['dssp'].detach().cpu().numpy()
        seq = batch['seqs'].detach().cpu().numpy()

        for j in range(len(names)):            
            p_aa, p_dssp, p_dssp_aa = [], [], []
            s_mask, d_mask = seq[j][eval_mask[j]], dssp[j][eval_mask[j]]
            for s, d in zip(s_mask, d_mask):
                p_aa.append(np.random.choice([0,1], replace = False, p = [1-df_aa[s], df_aa[s]]))
                p_dssp.append(np.random.choice([0,1], replace = False, p = [1-df_dssp[d], df_dssp[d]]))
                pi = df_aa_dssp.loc[(df_aa_dssp['dssp'] == d) & (df_aa_dssp['token'] == s)]['target'].item()
                p_dssp_aa.append(np.random.choice([0,1], replace = False, p = [1-pi, pi]))

            outs.append({'entry_ID': str(names[j]),
                         'seq': seq[j],
                         'p_aa': np.array(p_aa),
                         'p_dssp': np.array(p_dssp),
                         'p_aa_dssp': np.array(p_dssp_aa),
                         'target': target[j][eval_mask[j]],
                         'eval_mask': eval_mask[j],
                         'dssp': dssp[j]})
    
    return pd.DataFrame.from_records(outs)

def get_metrics(row, p):

    logits, labels = row[p], row['target']
    auroc, auprc, auprc_norm = utils.get_auroc(logits, labels)
    
    return auroc.item(), auprc.item(), auprc_norm.item()

def main(args):
    output_base = f'{args.method}_dummy'

    if args.missing_only or args.rex_only or args.unsuppressed:
        output_base = f'{output_base}_'
    if args.missing_only:
        output_base = f'{output_base}M'
    if args.rex_only:
        output_base = f'{output_base}R'
    if args.unsuppressed:
        output_base = f'{output_base}Y'
    
    config, config_dict = utils.load_config(f'configs/baseline.yml', return_dict=True)
    data = DynaData(config_dict['data'][args.method]['split'],
                        type = config_dict['data'][args.method]['type'],
                        crop_len = config_dict['data'][args.method]['crop_len'], 
                        cluster_file = config.data.cluster,
                        missing_only = args.missing_only,
                        rex_only = args.rex_only, 
                        pair_rep = config.data.pair_rep,
                        unsuppressed = args.unsuppressed,
                        return_dssp = True,
                        method = ('baseline', None))
    
    dataloader = DataLoader(dataset = data, 
                            batch_size = args.batch_size, 
                            shuffle = False, 
                            drop_last = False,
                            collate_fn = data.__collate_fn__)

    probs_df = get_data(dataloader)
    
    for k in ['aa', 'dssp', 'aa_dssp']:
        df_names = ['AUROC', 'AUPRC', 'AUPRC_norm']
        probs_df[df_names] = probs_df.apply(lambda row: get_metrics(row, f'p_{k}'), axis=1, result_type='expand')
        path = os.path.join(f'{args.save_dir}', f'{args.method}/{k}_{output_base}.json.zip')
        probs_df.to_json(path)
        auroc, auprc, auprc_norm = probs_df['AUROC'].mean(), probs_df['AUPRC'].mean(), probs_df['AUPRC_norm'].mean()
        print(f'{k}: AUROC {auroc}, AUPRC, {auprc}, normAUPRC: {auprc_norm}' )

    gc.collect()
    torch.cuda.empty_cache()

if __name__ =='__main__':
    parser = argparse.ArgumentParser(description='Baseline dummy classifier evaluation')

    parser.add_argument('--method', type=str, required=True)
    parser.add_argument('--rex_only', action='store_true')
    parser.add_argument('--missing_only', action='store_true')
    parser.add_argument('--unsuppressed', action='store_true')
    parser.add_argument('--seed', default=24, type=int)
    parser.add_argument('--batch_size', default=16, type=int)
    parser.add_argument('--save_dir', default='/scratch/users/gelnesr/nmr_esm/dummy')

    args = parser.parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    main(args)
