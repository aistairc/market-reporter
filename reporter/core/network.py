import itertools
from collections import OrderedDict
from typing import List, Tuple, Union

import torch
from torch import Tensor, nn
from torchtext.data import Batch

from reporter.util.config import Config
from reporter.util.constant import (
    GENERATION_LIMIT,
    N_LONG_TERM,
    N_SHORT_TERM,
    TIMESLOT_SIZE,
    Phase,
    SeqType)
from reporter.util.conversion import stringify_ric_seqtype


class Attention(nn.Module):
    '''This implementation is based on `Luong et al. (2015) <https://arxiv.org/abs/1508.04025>`_.
    '''

    def __init__(self):
        super(Attention, self).__init__()

    def forward(self, h_t: Tensor, h_s: Tensor) -> Tensor:
        return self.align(h_t, h_s)

    def align(self, h_t: Tensor, h_s: Tensor) -> Tensor:
        r'''
        .. math:
            a_{ij} =
                \frac{%
                    \exp\left(
                        \operatorname{score}\left(
                            \boldsymbol{h}^\text{target}_j, \boldsymbol{h}^\text{source}_i
                        \right)
                    \right)
                }{%
                    \sum_{\iota = 1}^I
                        \exp\left(
                            \operatorname{score}\left(
                                \boldsymbol{h}^\text{target}_j, \boldsymbol{h}^\text{source}_\iota
                            \right)
                        \right)
                }
        '''
        return nn.functional.softmax(self.score(h_t, h_s), dim=1)

    def score(self, h_t: Tensor, h_s: Tensor) -> Tensor:
        raise NotImplementedError


class GeneralAttention(Attention):

    def __init__(self, h_t_size: int, h_s_size: int):
        super(Attention, self).__init__()
        r'''
        Args:
            h_t_size (int): the size of target hidden state
            h_s_size (int): the size of source hidden state

        This calculates scores by
        ..math:
            \boldsymbol{h}^{target}_j
                \cdot
            \boldsymbol{W}^\text{attn} \boldsymbol{h}^\text{source}_i.
        '''
        self.w_a = nn.Linear(h_s_size, h_t_size, bias=False)

    def score(self, h_t: Tensor, h_s: Tensor) -> Tensor:
        return torch.bmm(self.w_a(h_s), h_t.transpose(1, 2))


class ConcatAttention(Attention):

    def __init__(self, h_t_size: int, h_s_size: int, v_a_size: int):
        r'''
        Args:
            h_t_size (int): Size of target hidden state
            h_s_size (int): Size of source hidden state
            v_a_size (int): Size of parameter :math:`\boldsymbol{v}^\text{attn}`

        This calculates scores by
        ..math:
            \boldsymbol{v}^{attn}
                \cdot
            \tanh\left(
                \boldsymbol{W}^\text{attn}
                    \left[
                        \boldsymbol{h}^\text{target};
                        \boldsymbol{h}^\text{source}
                    \right]
            \right)
        where :math:`[\boldsymbol{v}_1;\boldsymbol{v}_2]` denotes concatenation
        of :math:`\boldsymbol{v}_1` and :math:`\boldsymbol{v}_2`.
        '''

        super(Attention, self).__init__()
        self.v_a_transposed = nn.Linear(v_a_size, 1, bias=False)
        self.w_a_cat = nn.Linear(h_t_size + h_s_size, v_a_size, bias=False)

    def score(self, h_t: Tensor, h_s: Tensor) -> Tensor:
        return self.v_a_transposed(torch.tanh(self.w_a_cat(torch.cat((h_t, h_s), 2))))

    def align(self, h_t: Tensor, h_s: Tensor) -> Tensor:
        return nn.functional.softmax(self.score(h_t, h_s), dim=1)


def setup_attention(config: Config, seqtypes: List[SeqType]) -> Union[None, Attention]:

    enc_time_hidden_size = config.time_embed_size * len(seqtypes)

    if config.attn_type == 'general':
        # h_t·(W_a h_s)
        return GeneralAttention(config.dec_hidden_size, enc_time_hidden_size)
    elif config.attn_type == 'concat':
        # v_a·tanh(W[h_t;h_s])
        return ConcatAttention(h_t_size=config.dec_hidden_size,
                               h_s_size=config.enc_time_embed_size * len(seqtypes),
                               v_a_size=config.dec_hidden_size)
    else:
        return None


class Encoder(nn.Module):
    def __init__(self, config: Config, device: torch.device):

        super(Encoder, self).__init__()
        self.used_seqtypes = [SeqType.NormMovRefLong,
                              SeqType.NormMovRefShort,
                              SeqType.StdLong,
                              SeqType.StdShort] \
            if config.use_standardization \
            else [SeqType.NormMovRefLong,
                  SeqType.NormMovRefShort]
        self.used_rics = config.rics
        self.use_extra_rics = len(self.used_rics) > 1
        self.base_ric = config.base_ric
        self.extra_rics = [ric for ric in self.used_rics if ric != self.base_ric]
        self.base_ric_hidden_size = config.base_ric_hidden_size
        self.ric_hidden_size = config.ric_hidden_size
        self.hidden_size = config.enc_hidden_size
        self.n_layers = config.enc_n_layers
        self.prior_encoding = int(self.base_ric in self.used_rics)
        self.dropout = config.use_dropout
        self.device = device

        self.use_dropout = config.use_dropout
        self.ric_seqtype_to_mlp = dict()

        for (ric, seqtype) in itertools.product(self.used_rics, self.used_seqtypes):
            input_size = N_LONG_TERM \
                if seqtype.value.endswith('long') \
                else N_SHORT_TERM
            output_size = self.base_ric_hidden_size \
                if ric == self.base_ric \
                else self.ric_hidden_size
            mlp = MLP(input_size,
                      self.hidden_size,
                      output_size,
                      n_layers=self.n_layers).to(self.device)
            self.ric_seqtype_to_mlp[(ric, seqtype)] = mlp

        lengths = [N_LONG_TERM if seqtype.value.endswith('long') else N_SHORT_TERM
                   for (_, seqtype) in itertools.product(self.used_rics, self.used_seqtypes)]
        total_length = sum(lengths)
        self.cat_hidden_size = \
            total_length + self.prior_encoding * len(self.used_seqtypes) * self.base_ric_hidden_size \
            if len(self.used_rics) == 1 \
            else self.prior_encoding * len(self.used_seqtypes) * self.base_ric_hidden_size + \
            (len(lengths) - self.prior_encoding * len(self.used_seqtypes)) * self.ric_hidden_size

        self.dense = nn.Linear(self.cat_hidden_size, self.hidden_size)

        if self.use_dropout:
            self.drop = nn.Dropout(p=0.30)

    def forward(self,
                batch: Batch,
                mini_batch_size: int) -> Tuple[Tensor, Tensor]:

        L = OrderedDict()  # low-level representation
        H = OrderedDict()  # high-level representation

        attn_vector = []

        for (ric, seqtype) in itertools.product(self.used_rics, self.used_seqtypes):

            vals = getattr(batch, stringify_ric_seqtype(ric, seqtype)).to(self.device)

            if seqtype in [SeqType.NormMovRefLong, SeqType.NormMovRefShort]:
                # Switch the source to one which is not normalized
                # to make our implementation compatible with Murakami 2017
                L_seqtype = SeqType.MovRefLong \
                    if seqtype == SeqType.NormMovRefLong \
                    else SeqType.MovRefShort
                L[(ric, seqtype)] = getattr(batch, stringify_ric_seqtype(ric, L_seqtype)).to(self.device)
                H[(ric, seqtype)] = self.ric_seqtype_to_mlp[(ric, seqtype)](vals)
            else:
                L[(ric, seqtype)] = vals
                H[(ric, seqtype)] = self.ric_seqtype_to_mlp[(ric, seqtype)](L[(ric, seqtype)])

        for ric in self.extra_rics:
            attn_vector.extend([H[(ric, seq)] for seq in self.used_seqtypes])

        enc_hidden = torch.cat(list(H.values()), 1) \
            if self.use_extra_rics \
            else torch.cat(list(L.values()) + list(H.values()), 1)  # Murakami model

        enc_hidden = self.dense(enc_hidden)

        if self.use_dropout:
            enc_hidden = self.drop(enc_hidden)

        if len(attn_vector) > 0:
            attn_vector = torch.cat(attn_vector, 1)
            attn_vector = attn_vector.view(mini_batch_size, len(self.extra_rics), -1)

        return (enc_hidden, attn_vector)


class Decoder(nn.Module):
    def __init__(self,
                 config: Config,
                 output_vocab_size: int,
                 attn: Union[None, Attention],
                 device: torch.device):

        super(Decoder, self).__init__()

        self.device = device
        self.dec_hidden_size = config.dec_hidden_size
        self.word_embed_size = config.word_embed_size
        self.time_embed_size = config.time_embed_size
        self.attn = attn

        self.word_embed_layer = nn.Embedding(output_vocab_size, self.word_embed_size, padding_idx=0)
        self.time_embed_layer = nn.Embedding(TIMESLOT_SIZE, self.time_embed_size)
        self.output_layer = nn.Linear(self.dec_hidden_size, output_vocab_size)
        self.softmax = nn.LogSoftmax(dim=1)

        self.dec_hidden_size = self.dec_hidden_size
        self.input_hidden_size = self.time_embed_size + self.word_embed_size
        self.recurrent_layer = nn.LSTMCell(self.input_hidden_size, self.dec_hidden_size)

        if isinstance(attn, Attention):
            self.enc_hidden_size = config.enc_hidden_size
            attn_size = self.enc_hidden_size + self.dec_hidden_size
            self.linear_attn = nn.Linear(attn_size, self.dec_hidden_size)

    def init_hidden(self, batch_size: int) -> Tuple[Tensor, Tensor]:
        zeros = torch.zeros(batch_size, self.dec_hidden_size, device=self.device)
        self.h_n = zeros
        self.c_n = zeros
        return (self.h_n, self.c_n)

    def forward(self,
                word: Tensor,
                time: Tensor,
                seq_ric_tensor: Tensor,
                batch_size: int) -> Tuple[Tensor, Tensor]:

        weight = 0.0
        word_embed = self.word_embed_layer(word).view(batch_size, self.word_embed_size)
        time_embed = self.time_embed_layer(time).view(batch_size, self.time_embed_size)
        stream = torch.cat((word_embed, time_embed), 1)
        self.h_n, self.c_n = self.recurrent_layer(stream, (self.h_n, self.c_n))
        hidden = self.h_n

        if isinstance(self.attn, Attention):
            _, num_copy, _ = seq_ric_tensor.size()

            if isinstance(self.attn, ConcatAttention):
                copied_hidden = hidden.expand(num_copy, batch_size, self.hidden_size)
                copied_hidden = torch.transpose(copied_hidden, 0, 1)
            else:
                copied_hidden = hidden.unsqueeze(1)
            weight = self.attn(copied_hidden, seq_ric_tensor)
            weighted_ric = torch.bmm(weight.view(batch_size, -1, num_copy),
                                     seq_ric_tensor.view(batch_size, num_copy, -1))
            weighted_ric = weighted_ric.squeeze()
            hidden = torch.tanh(self.linear_attn(torch.cat((hidden, weighted_ric), 1)))
            self.h_n = hidden

        output = self.softmax(self.output_layer(hidden))
        return (output, weight)


class MLP(nn.Module):
    def __init__(self,
                 input_size: int,
                 mid_size: int,
                 output_size: int,
                 n_layers: int = 3,
                 activation_function: str = 'tanh'):
        '''Multi-Layer Perceptron
        '''

        super(MLP, self).__init__()
        self.n_layers = n_layers

        assert(n_layers >= 1)

        if activation_function == 'tanh':
            self.activation_function = nn.Tanh()
        elif activation_function == 'relu':
            self.activation_function = nn.ReLU()
        else:
            raise NotImplementedError

        self.MLP = nn.ModuleList()
        if n_layers == 1:
            self.MLP.append(nn.Linear(input_size, output_size))
        else:
            self.MLP.append(nn.Linear(input_size, mid_size))
            for _ in range(n_layers - 2):
                self.MLP.append(nn.Linear(mid_size, mid_size))
            self.MLP.append(nn.Linear(mid_size, output_size))

    def forward(self, x: Tensor) -> Tensor:
        out = x
        for i in range(self.n_layers):
            out = self.MLP[i](out)
            out = self.activation_function(out)
        return out


class EncoderDecoder(nn.Module):
    def __init__(self,
                 encoder: Encoder,
                 decoder: Decoder,
                 device: torch.device):
        super(EncoderDecoder, self).__init__()

        self.device = device
        self.encoder = encoder.to(self.device)
        self.decoder = decoder.to(self.device)

        self.weight_lambda = 10 ** 0  # for supervised attention

    def forward(self,
                batch: Batch,
                mini_batch_size: int,
                tokens: Tensor,
                time_embedding: Tensor,
                criterion: nn.NLLLoss,
                phase: Phase) -> Tuple[nn.NLLLoss, Tensor, Tensor]:

        self.decoder.init_hidden(mini_batch_size)
        self.decoder.h_n, attn_vector = self.encoder(batch, mini_batch_size)

        loss = 0.0
        n_tokens, _ = tokens.size()
        decoder_input = tokens[0]
        time_embedding = time_embedding.squeeze()

        pred = []
        attn_weight = []
        pred.append(decoder_input.cpu().numpy())

        if phase == Phase.Train:
            for i in range(1, n_tokens):
                decoder_output, weight = \
                    self.decoder(decoder_input, time_embedding, attn_vector, mini_batch_size)
                loss += criterion(decoder_output, tokens[i])

                topv, topi = decoder_output.data.topk(1)
                pred.append([t[0] for t in topi.cpu().numpy()])
                if self.decoder.attn:
                    weight = weight.squeeze()
                    attn_weight.append(weight)

                decoder_input = tokens[i]

        else:
            for i in range(1, GENERATION_LIMIT):
                decoder_output, weight = \
                    self.decoder(decoder_input, time_embedding, attn_vector, mini_batch_size)
                if i < n_tokens:
                    loss += criterion(decoder_output, tokens[i])

                topv, topi = decoder_output.detach().topk(1)
                pred.append([t[0] for t in topi.cpu().numpy()])
                if self.decoder.attn:
                    weight = weight.squeeze(2).cpu().numpy()
                    attn_weight.append(weight)

                decoder_input = topi.squeeze()

        return (loss, pred, attn_weight)
