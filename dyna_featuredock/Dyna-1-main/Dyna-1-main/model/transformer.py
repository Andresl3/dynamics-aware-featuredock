import math
import torch
import torch.nn as nn
from torch.autograd import Variable
from torch.nn.utils import weight_norm

class Transformer(nn.Module):
    def __init__(self, 
                 in_dim,
                 nlayers = 12,
                 nheads = 6,
                 dropout = 0.1,
                 hidden_size = 2048,
                 layer = -1):
        super().__init__()
        """
        Instantiation of a Transformer classifier

        Args:
            in_dim: (int) input dimension size
            nlayers: (int) number of layers for Transformer classifier (default: 12)
            nheads: (int) number of heads for Transformer classifier (default: 6)
            dropout: (float) dropout rate for Transformer classifier (default: 0.1)
            hidden_size: (int) dimension size of model
            layer: (int) layer to use from model (default: -1)
        """
                
        self.layer = layer
        self.norm1 = nn.LayerNorm(in_dim, eps = 1e-12, elementwise_affine = True)
        self.norm2 = nn.LayerNorm(in_dim, eps = 1e-12, elementwise_affine = True)
        encoder_layer = nn.TransformerEncoderLayer(d_model = in_dim, 
                                                   nhead = nheads,
                                                   dim_feedforward = hidden_size, 
                                                   dropout = dropout,
                                                   norm_first = True,
                                                   batch_first = True)
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers = nlayers)
        self.output_layer = nn.Linear(in_dim, 1)
        self.apply(self._init_weights)

    def forward(self, embedding, mask):
        x = embedding
        if not torch.is_tensor(embedding) and self.layer != -1:
            x = embedding[self.layer]
        x = self.norm1(x)         
        x = self.encoder(x, src_key_padding_mask=mask)        
        x = self.norm2(x) 
        x = self.output_layer(x)   
        return x

    @staticmethod
    def _init_weights(module):
        """ Initialize the weights """
        if isinstance(module, nn.LayerNorm):
            module.bias.data.zero_()
            module.weight.data.fill_(1.0)
        if isinstance(module, nn.Linear) and module.bias is not None:
            module.bias.data.zero_()