import yaml
import argparse
import numpy as np
import torch
import torch.nn as nn
from torcheval.metrics.functional import binary_auroc, binary_auprc
from sklearn.metrics import recall_score, precision_score
import mdtraj as md

def calc_dssp(pdb_file):
    """ Calculate DSSP for a PDB file """
    obj = md.load_pdb(pdb_file)

    return ''.join([x for x in md.compute_dssp(obj, simplified=True).tolist()[0]]).replace(' ','.')

def dict2namespace(config):
    """ Generate namespace given a config file (dictionary) """
    namespace = argparse.Namespace()
    
    for key, value in config.items():
        if isinstance(value, dict):
            new_value = dict2namespace(value)
        else:
            new_value = value
        setattr(namespace, key, new_value)
    
    return namespace

def load_config(path, return_dict=False):
    """ Load a config file """

    with open(path, "r") as f:
        config_dict = yaml.safe_load(f)
    
    config = dict2namespace(config_dict)
    
    if return_dict:
        return config, config_dict
    
    return config

def get_loss(logits, labels, mask):
    """Compute masked loss."""

    loss = nn.BCEWithLogitsLoss(reduction='none', pos_weight = torch.tensor(1.0))(logits, labels)
    masked_loss = loss * mask
    mean_loss = masked_loss.sum() / mask.sum()
    return masked_loss.sum(), mask.sum(), mean_loss

def get_masked(logits, labels, mask):
    """Mask logits and labels using a given mask"""
    if isinstance(mask, np.ndarray):
        masked_logits = logits[mask.astype(bool)]
        masked_labels = labels[mask.astype(bool)]
    else:
        masked_logits = logits[mask.bool()].view(-1)
        masked_labels = labels[mask.bool()].view(-1)

    return masked_logits, masked_labels

def get_auroc(masked_logits, masked_labels):
    """Evaluate AUROC, AUPRC, and norm AUPRC for given logits, labels"""

    if isinstance(masked_labels, np.ndarray):
        masked_labels = torch.tensor(masked_labels)
    if isinstance(masked_logits, np.ndarray):
        masked_logits = torch.tensor(masked_logits)
    
    roc = binary_auroc(masked_logits, masked_labels)
    prc = binary_auprc(masked_logits, masked_labels)
    
    baseline = masked_labels.sum()/len(masked_labels)
    
    return abs(roc), abs(prc), abs(prc)-baseline

def get_pr_metrics(masked_logits, masked_labels, t):
    """Evaluate F1-score, precision, recall for given logits, labels, and threshold"""

    pred_labels = (masked_logits > t).astype(int)
    r = recall_score(masked_labels, pred_labels)
    p = precision_score(masked_labels,pred_labels)

    f1 = 2 * r * p / (r+p+1e-8)
    n_labels_tot = len(masked_labels)
    n_pos = masked_labels.sum()
    
    return f1, p, r, n_labels_tot, n_pos

def prob_adjusted(logits, prior=0.05):
    """Adjust outputted logits to reflect a probability between 0.0-1.0"""
    
    adjustment = np.log(prior/(1-prior)) 
    prob = torch.sigmoid(logits-adjustment)
    return prob