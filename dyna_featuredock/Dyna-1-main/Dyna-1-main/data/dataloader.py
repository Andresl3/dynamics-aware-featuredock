import numpy as np
import warnings
import random
import torch
import os
import pickle
import data.vocab as vocab
import pandas as pd
from typing import Tuple, List, Any
from esm.sdk.api import ESMProtein
from transformers import AutoTokenizer
import utils

class DynaData(torch.utils.data.Dataset):
    """
    For each protein, we use a pkl file that contains:
        seq: The domain sequence, stored as an L-length string
        assns: string containing labels of dynamics type
    """

    def __init__(
        self,
        split,
        type = 'missing',
        sample_clusters = False,
        cluster_file = None,
        crop_len = 300,
        missing_only = False,
        rex_only = False,
        unsuppressed = False,
        method = None,
        pair_rep = None,
        return_dssp = False
    ):
        super().__init__()

        self.return_dssp = return_dssp
        self.crop_len = crop_len
        self.sample_clusters = sample_clusters
        self.label_tokenizer = vocab.label_tokenizer(type = type, 
                                                     missing_only = missing_only,
                                                     rex_only = rex_only,
                                                     unsuppressed = unsuppressed)
        
        # tokenization is the same for all ESM models, use the lightest one 
        self.tokenizer = AutoTokenizer.from_pretrained(f"facebook/esm2_t6_8M_UR50D")
        self.proline = self.tokenizer.get_vocab()['P']
  
        self.method = method[0]
        self.model = method[1]

        if isinstance(split, str):
            split = [split]
                
        self.all_names, self.names = [], []

        # read in all pdb names
        for fil in split:
            filename = f'data/split_files/{fil}.txt'
            with open(filename,'r') as f:
                self.all_names.extend(f.read().splitlines())

        # set up cluster sampling
        if self.sample_clusters:
            self.cluster_info = pd.read_csv(f'data/{cluster_file}.tsv', sep='\t')
            self.cluster_info['cluster'] = self.cluster_info.apply(lambda row: row['cluster'], axis=1)
            for nm in self.all_names:
                subset = self.cluster_info.loc[self.cluster_info.entry_ID==nm]
                if len(subset) == 0:
                    print('NO!', nm)
                cluster_ind = subset['cluster'].iloc[0]
                if cluster_ind not in self.names:
                    self.names.append(cluster_ind)
        else:
            self.names = self.all_names

        self.pair_rep_dir = pair_rep

    def __len__(self):
        return len(self.names)

    def __baseline_get_item__(self, name, obj, crop_start):
        if crop_start > -1:
            sequence = obj['sequence'][crop_start:crop_start+self.crop_len]
        else:
            sequence = obj['sequence'][:self.crop_len]
        
        sequence_tokens = self.tokenizer.encode(sequence, 
                                           add_special_tokens=False,
                                           padding='max_length',
                                           max_length=self.crop_len,
                                           return_tensors='np').squeeze()
        
        # set mask to 1 for length of seq, padded tokens then are 0
        eval_mask = np.zeros_like(sequence_tokens)
        eval_mask[:len(sequence)] = 1

        sequence_id = sequence_tokens != 0

        # mask prolines in eval
        eval_mask[sequence_tokens==self.proline] = 0
        
        return sequence_tokens, sequence_id, eval_mask

    def __af2_get_item__(self, name, obj, crop_start):
        """
        Prepares input for the AF2-pair model
        """
        
        pair_rep = np.load(f"{self.pair_rep_dir}/{name}.npy")
        labels, seq = obj['label'], obj['sequence']

        if crop_start > -1:
            pair_rep = pair_rep[crop_start:crop_start+self.crop_len,
                crop_start:crop_start+self.crop_len, :]
            labels = labels[crop_start:crop_start+self.crop_len]
            seq = seq[crop_start:crop_start+self.crop_len]

        eval_mask = np.zeros((pair_rep.shape[0],))
        
        prolines = [i for i, aa in enumerate(seq) if aa == 'P']
        eval_mask[:len(labels)] = 1

        sequence_id = eval_mask != 0
        eval_mask[prolines] = 0
        x = pair_rep.shape[0]

        eval_mask = np.pad(eval_mask, (0, self.crop_len - len(eval_mask)), mode='constant')
        sequence_id = np.pad(sequence_id, (0, self.crop_len - len(sequence_id)), mode='constant')
        if x < self.crop_len:
            pair_rep = np.pad(pair_rep, ((0, self.crop_len - x), (0, self.crop_len - x), (0, 0)), mode='constant', constant_values=0)
            
        return pair_rep, sequence_id, eval_mask

    def __esm3_get_item__(self, name, crop_start, data_path = 'esm3_data/'):
        """
        Prepares input for the ESM3 model
        """
        pkl_fname = os.path.join(data_path, f"{name}.pkl")
        
        try:
            with open(pkl_fname, "rb") as f:
                esm_data = pickle.load(f)
        except:
            print(f'writing pkl for {name} {crop_start}')
            pdb_path = f'pdbs/{name}.pdb'
            protein = ESMProtein.from_pdb(pdb_path)
            
            self.model.eval()
            encoder = self.model.model.encode(protein)
            self.model.train()

            seq = encoder.sequence.cpu().detach()[1:-1][:700]
            struct = encoder.structure.cpu().detach()[1:-1][:700]

            sequence_tokens = np.full(700, 1, dtype=np.int32) ## sequence pad token is 1
            structure_tokens = np.full(700, 4099, dtype=np.int32) ## structure pad token is 4099
            
            sequence_tokens[:len(seq)] = seq
            structure_tokens[:len(struct)] = struct

            sequence_id = sequence_tokens != 1
            
            obj ={'name': name, 'len': len(seq), 'seq_tokens': sequence_tokens, 
                  'struct_tokens': structure_tokens, 'sequence_id': sequence_id}

            with open(pkl_fname, 'wb') as f:
                pickle.dump(obj, f)
        
        with open(pkl_fname, "rb") as f:
            esm_data = pickle.load(f)

        if crop_start > -1:
            sequence_tokens = esm_data['seq_tokens'][crop_start:crop_start+self.crop_len]
            structure_tokens = esm_data['struct_tokens'][crop_start:crop_start+self.crop_len]
            sequence_id = esm_data['sequence_id'][crop_start:crop_start+self.crop_len]
        else:
            sequence_tokens = esm_data['seq_tokens'][:self.crop_len]
            structure_tokens = esm_data['struct_tokens'][:self.crop_len]
            sequence_id = esm_data['sequence_id'][:self.crop_len]

        eval_mask = np.zeros_like(sequence_tokens)
        eval_mask[:esm_data['len']] = 1
        eval_mask[sequence_tokens==self.proline] = 0

        return sequence_tokens, structure_tokens, sequence_id, eval_mask

    def __esm2_get_item__(self, obj, crop_start):
        """
        Prepares input for the ESM2 model
        """
        sequence = obj['sequence'].replace(' ','')
        if crop_start > -1:
            sequence = sequence[crop_start:crop_start+self.crop_len]

        sequence_tokens = self.tokenizer.encode(sequence, 
                                           add_special_tokens=False,
                                           padding='max_length',
                                           max_length=self.crop_len,
                                           return_tensors='np').squeeze()
        
        # Set mask to 1 for length of sequence, padded tokens then are 0
        eval_mask = np.zeros_like(sequence_tokens)
        eval_mask[:len(sequence)] = 1
        sequence_id = eval_mask != 0
        eval_mask[sequence_tokens==self.proline] = 0
        
        return sequence_tokens, sequence_id, eval_mask
    
    def __get_dssp__(self, name, crop_start):
        """
        Prepares DSSP information for a given sequence
        """
        try:
            dssp_csv = pd.read_csv('data/dssp.csv')
            entry = dssp_csv.loc[dssp_csv.PDB == str(name)].iloc[0]
        except:
            entry = {}
            entry['DSSP'] = utils.calc_dssp(f'pdbs/{name}.pdb')

        assert len(entry) > 0
        if crop_start ==-1:
            dssp_data = entry['DSSP'].replace(' ','')[:self.crop_len]
        else:
            dssp_data = entry['DSSP'].replace(' ','')[crop_start:crop_start + self.crop_len]

        dssp = np.zeros(self.crop_len)
        inds = [i for i, char in enumerate(dssp_data) if char=='C']
        dssp[inds] = 1.0
        
        inds = [i for i, char in enumerate(dssp_data) if char=='H']
        dssp[inds] = 2.0

        return dssp
    
    def __getitem__(self, idx):
        """
        Returns a dict with the appropriate entries for each model
        """
        exists = -1
        while exists == -1:
            name = self.names[idx]
            if self.sample_clusters:
                roptions = list(self.cluster_info.loc[self.cluster_info.cluster==name]['entry_ID'].values)
                options = [opt for opt in roptions if opt in self.all_names]
                name = random.choice(options)
            pkl_fname = f"data/mBMRB_data/{name}.pkl"
            
            try:
                with open(pkl_fname, "rb") as f:
                    obj = pickle.load(f)
                exists = 1
            except:
                print(f'{pkl_fname} not found')

        assns = obj['label']
        assns = vocab.mask_termini(assns)

        crop_start = -1
        if len(assns) > self.crop_len:
            crop_start = np.random.choice(range(0, len(assns)-self.crop_len))   
            assns = assns[crop_start:crop_start + self.crop_len]

        labels = self.label_tokenizer.convert_tokens_to_ids(assns, pad_to_length=self.crop_len)
        labels = np.asarray(labels, np.int64)

        dssp = None
        if self.return_dssp:
            dssp = self.__get_dssp__(name, crop_start)
        if 'esm3' in self.method:
            sequence, structure, sequence_id, eval_mask = self.__esm3_get_item__(name, crop_start)
        elif 'esm2' in self.method:
            sequence, sequence_id, eval_mask = self.__esm2_get_item__(obj, crop_start)
        elif 'af2' in self.method:
            pair_rep, sequence_id, eval_mask = self.__af2_get_item__(name, obj, crop_start)
        elif 'baseline' in self.method:
            sequence, sequence_id, eval_mask = self.__baseline_get_item__(name, obj, crop_start)
        
        # Mask termini for eval. A -1 label corresponds to indices that are getting masked in vocabs
        eval_mask[labels==-1] = 0

        if 'esm2' in self.method:
            return sequence, sequence_id, eval_mask, labels, name, dssp
        elif 'esm3' in self.method:
            return sequence, structure, sequence_id, eval_mask, labels, name, dssp
        elif 'af2' in self.method:
            return pair_rep, labels, sequence_id, eval_mask, name, dssp
        elif 'baseline' in self.method:
            return sequence, labels, sequence_id, eval_mask, name, dssp

    def __collate_fn__(self, batch: List[Tuple[Any, ...]]):

        if 'baseline' in self.method:
            seqs, labels, sequence_id, eval_mask, names, dssp = tuple(zip(*batch))
            seqs = torch.tensor(np.array(seqs))

            labels = torch.from_numpy(np.array(labels)).float()
            eval_mask = torch.from_numpy(np.array(eval_mask))    
            if self.return_dssp:
                dssp = torch.from_numpy(np.array(dssp))
            sequence_id = torch.from_numpy(np.array(sequence_id))

            output = {'names': names, 'seqs': seqs, 'seq_id': sequence_id, 
                        'targets': labels, 'eval_mask': eval_mask, 'dssp': dssp}
            return output
        
        elif 'af2' in self.method:
            pair_reps, labels, sequence_id, eval_mask, names, dssp = tuple(zip(*batch))

            pair_reps = torch.from_numpy(np.array(pair_reps, dtype=np.float64))
            labels = torch.from_numpy(np.array(labels)).float()
            eval_mask = torch.from_numpy(np.array(eval_mask))
            sequence_id = torch.from_numpy(np.array(sequence_id, dtype=bool))

            if self.return_dssp:
                dssp = torch.from_numpy(np.array(dssp))
            output = {'names': names, 'pair_reps': pair_reps, 'targets': labels, "seq_id": sequence_id, 
                      'eval_mask': eval_mask, 'dssp': dssp}
            return output
        
        elif 'esm2' in self.method:
            seqs, sequence_id, eval_mask, label, names, dssp = tuple(zip(*batch))
            seqs = torch.from_numpy(np.array(seqs))
            structs = None
            sequence_id = torch.from_numpy(np.array(sequence_id))

        elif 'esm3' in self.method:
            seqs, structs, sequence_id, eval_mask, label, names, dssp = tuple(zip(*batch))
            seqs = torch.from_numpy(np.array(seqs))
            structs = torch.from_numpy(np.array(structs))
            sequence_id = torch.from_numpy(np.array(sequence_id))

        eval_mask = torch.from_numpy(np.array(eval_mask))
        label = torch.from_numpy(np.array(label)).float()
        if self.return_dssp:
            dssp = torch.from_numpy(np.array(dssp))

        output = {'seqs': seqs, "structs": structs, "seq_id": sequence_id, "eval_mask": eval_mask, 
                     'targets': label, 'names': names, 'dssp': dssp}

        return output
