"""
Modified FeatureDock transformer that accepts an extra dynamics token.

Original layout:  (N, num_shells * feature_per_shell) → reshape to (N, feature_per_shell, num_shells)
                  feature_per_shell = 80, num_shells = 6
                  → 80 tokens, each a 6-element vector

Dyna layout:      (N, num_shells * feature_per_shell + num_shells)
                  e.g. (N, 486) = (N, 480 + 6)
                  → 81 tokens: 80 physicochemical + 1 dynamics
                  dynamics token = per-shell flexibility means, shape (num_shells,) = (6,)

Only BertModel.forward() changes; everything else is identical to the original.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from models.transformer_models import BertSelfAttention, BertLayer


class DynaBertModel(nn.Module):
    """
    FeatureDock transformer + one extra dynamics token (token index 80).

    Parameters
    ----------
    num_shells        : number of FEATURE shells (default 6)
    feature_per_shell : physicochemical properties per shell (default 80)
    hidden_size       : transformer hidden dim
    intermediate_size : FFN intermediate dim
    num_hidden_layers : number of transformer layers
    num_attention_heads
    use_dynamics      : if False, behaves identically to original BertModel
    """

    def __init__(self,
                 num_shells=6,
                 feature_per_shell=80,
                 hidden_size=20,
                 intermediate_size=80,
                 num_hidden_layers=5,
                 num_attention_heads=4,
                 max_position_embeddings=100,
                 layer_norm_eps=1e-12,
                 hidden_dropout_prob=0.5,
                 attention_probs_dropout_prob=0.1,
                 use_dynamics=True):
        super().__init__()

        self.num_shells = num_shells
        self.feature_per_shell = feature_per_shell
        self.use_dynamics = use_dynamics
        # +1 token if dynamics enabled
        n_tokens = feature_per_shell + (1 if use_dynamics else 0)
        self.n_tokens = n_tokens

        self.norm_layer = nn.BatchNorm2d(feature_per_shell)
        self.cls_embedding = nn.Embedding(1, hidden_size)
        # project each token's num_shells-dim vector to hidden_size
        self.word2dense = nn.Linear(num_shells, hidden_size)
        self.pos_embedding = nn.Embedding(max_position_embeddings, hidden_size)
        self.embed_layer_norm = nn.LayerNorm(hidden_size, eps=layer_norm_eps)
        self.embed_dropout = nn.Dropout(hidden_dropout_prob)
        position_ids = torch.arange(max_position_embeddings).unsqueeze(0)
        self.register_buffer('position_ids', position_ids)

        self.bert_layers = nn.ModuleList([
            BertLayer(hidden_size, intermediate_size, layer_norm_eps,
                      hidden_dropout_prob, num_attention_heads,
                      attention_probs_dropout_prob)
            for _ in range(num_hidden_layers)
        ])

    def embed(self, feature_batch):
        """
        feature_batch : (N, n_tokens, num_shells)
                        n_tokens = 80 (base) or 81 (with dynamics)
        """
        device = feature_batch.device
        bs, seq_len, _ = feature_batch.shape
        cls_embeds = self.cls_embedding(
            torch.zeros((bs, 1), dtype=torch.long, device=device))     # (N, 1, H)
        inputs_embeds = self.word2dense(feature_batch)                  # (N, seq_len, H)
        inputs_embeds = torch.cat([cls_embeds, inputs_embeds], dim=1)  # (N, seq_len+1, H)
        pos_ids = self.position_ids[:, :seq_len + 1].to(device)
        pos_embeds = self.pos_embedding(pos_ids)
        embeds = inputs_embeds + pos_embeds
        embeds = self.embed_layer_norm(embeds)
        embeds = self.embed_dropout(embeds)
        return embeds

    def encode(self, hidden_states):
        for layer in self.bert_layers:
            hidden_states = layer(hidden_states)
        return hidden_states

    def forward(self, feature_batch):
        """
        feature_batch : (N, num_shells * feature_per_shell [+ num_shells])
                       = (N, 480) or (N, 486)

        Returns dict with 'pooler_output' and 'last_hidden_state'.
        """
        if self.use_dynamics:
            # split: first 480 = physicochemical, last 6 = dynamics token
            phys = feature_batch[:, :self.num_shells * self.feature_per_shell]
            dyn  = feature_batch[:, self.num_shells * self.feature_per_shell:]  # (N, 6)
            # reshape phys: (N, 80, 6)
            h = phys.view(-1, self.num_shells, self.feature_per_shell)
            h = h.permute(0, 2, 1)                         # (N, 80, 6)
            # dynamics token: (N, 1, 6)
            dyn = dyn.view(-1, 1, self.num_shells)
            h = torch.cat([h, dyn], dim=1)                  # (N, 81, 6)
        else:
            h = feature_batch.view(-1, self.num_shells, self.feature_per_shell)
            h = h.permute(0, 2, 1)                          # (N, 80, 6)

        embedding_output = self.embed(h)
        sequence_output = self.encode(embedding_output)
        first_tk = sequence_output[:, 0]
        return {'last_hidden_state': sequence_output, 'pooler_output': first_tk}


class DynaBertSentClassifier(nn.Module):
    """
    Drop-in replacement for BertSentClassifier that supports the dynamics token.
    """

    def __init__(self,
                 n_class,
                 num_shells=6,
                 feature_per_shell=80,
                 hidden_size=20,
                 intermediate_size=80,
                 num_hidden_layers=5,
                 num_attention_heads=4,
                 max_position_embeddings=100,
                 layer_norm_eps=1e-12,
                 hidden_dropout_prob=0.5,
                 attention_probs_dropout_prob=0.1,
                 use_dynamics=True,
                 option='finetune'):
        super().__init__()
        self.bert = DynaBertModel(
            num_shells=num_shells,
            feature_per_shell=feature_per_shell,
            hidden_size=hidden_size,
            intermediate_size=intermediate_size,
            num_hidden_layers=num_hidden_layers,
            num_attention_heads=num_attention_heads,
            max_position_embeddings=max_position_embeddings,
            layer_norm_eps=layer_norm_eps,
            hidden_dropout_prob=hidden_dropout_prob,
            attention_probs_dropout_prob=attention_probs_dropout_prob,
            use_dynamics=use_dynamics,
        )
        for param in self.bert.parameters():
            param.requires_grad = (option == 'finetune')

        self.dropout = nn.Dropout(hidden_dropout_prob)
        self.linear = nn.Linear(hidden_size, n_class)

    def forward(self, feature_batch):
        result = self.bert(feature_batch)
        h = result['pooler_output']
        return self.linear(self.dropout(h))
