from logging import Logger
from typing import Dict, List

import numpy
import torch
from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
from torchtext.data import Iterator
from torchtext.vocab import Vocab

from fag.core.network import Attention, EncoderDecoder
from fag.core.operation import replace_tags_with_vals, get_latest_closing_vals
from fag.util.constant import SEED, Code, Phase, SeqType, SpecialToken
from fag.util.conversion import stringify_ric_seqtype
from fag.util.tool import takeuntil
from fag.postprocessing.text import remove_bos


class RunResult:
    def __init__(self,
                 loss: float,
                 article_ids: List[str],
                 gold_sents: List[List[str]],
                 gold_sents_num: List[List[str]],
                 pred_sents: List[List[str]],
                 pred_sents_num: List[List[str]]):

        self.loss = loss
        self.article_ids = article_ids
        self.gold_sents = gold_sents
        self.gold_sents_num = gold_sents_num
        self.pred_sents = pred_sents
        self.pred_sents_num = pred_sents_num


def run(X: Iterator,
        vocab: Vocab,
        model: EncoderDecoder,
        optimizer: Dict[SeqType, torch.optim.Optimizer],
        criterion: torch.nn.modules.Module,
        phase: Phase,
        logger: Logger) -> RunResult:

    if phase in [Phase.Valid, Phase.Test]:
        model.eval()
    else:
        model.train()

    numpy.random.seed(SEED)

    accum_loss = 0.0
    all_article_ids = []
    all_gold_sents = []
    all_pred_sents = []
    all_gold_sents_with_number = []
    all_pred_sents_with_number = []
    attn_weights = []

    for batch in X:

        article_ids = batch.article_id
        times = batch.time
        tokens = batch.token
        raw_short_field = stringify_ric_seqtype(Code.N225.value, SeqType.RawShort)
        latest_vals = [x for x in getattr(batch, raw_short_field).data[:, 0]]
        raw_long_field = stringify_ric_seqtype(Code.N225.value, SeqType.RawLong)
        latest_closing_vals = get_latest_closing_vals(batch, raw_long_field, times)
        max_n_tokens, _ = tokens.size()

        # Forward
        loss, pred, attn_weight = model(batch, batch.batch_size, tokens, times, criterion, phase)

        if phase == Phase.Train:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        if isinstance(model.decoder.attn, Attention):
            attn_weight = numpy.array(list(zip(*attn_weight)))
            attn_weights.extend(attn_weight)

        all_article_ids.extend(article_ids)

        i_eos = vocab.stoi[SpecialToken.EOS.value]
        # Recover words from ids removing BOS and EOS from gold sentences for evaluation
        gold_sents = [remove_bos([vocab.itos[i] for i in takeuntil(i_eos, sent)])
                      for sent in zip(*tokens.cpu().numpy())]
        all_gold_sents.extend(gold_sents)

        pred_sents = [remove_bos([vocab.itos[i] for i in takeuntil(i_eos, sent)]) for sent in zip(*pred)]
        all_pred_sents.extend(pred_sents)

        if phase == Phase.Test:
            z_iter = zip(article_ids, gold_sents, pred_sents, latest_vals, latest_closing_vals)
            for (article_id, gold_sent, pred_sent, latest_val, latest_closing_val) in z_iter:

                bleu = sentence_bleu([gold_sent],
                                     pred_sent,
                                     smoothing_function=SmoothingFunction().method1)

                gold_sent_num = replace_tags_with_vals(gold_sent, latest_closing_val, latest_val)
                all_gold_sents_with_number.append(gold_sent_num)

                pred_sent_num = replace_tags_with_vals(pred_sent, latest_closing_val, latest_val)
                all_pred_sents_with_number.append(pred_sent_num)

                description = \
                    '\n'.join(['=== {} ==='.format(phase.value.upper()),
                               'Article ID: {}'.format(article_id),
                               'Gold (tag): {}'.format(', '.join(gold_sent)),
                               'Gold (num): {}'.format(', '.join(gold_sent_num)),
                               'Pred (tag): {}'.format(', '.join(pred_sent)),
                               'Pred (num): {}'.format(', '.join(pred_sent_num)),
                               'BLEU: {:.5f}'.format(bleu),
                               'Loss: {:.5f}'.format(loss.item() / max_n_tokens),
                               'Latest: {:.2f}'.format(latest_val),
                               'Closing: {:.2f}'.format(latest_closing_val)])
                logger.info(description)  # TODO: info → debug in release

        accum_loss += loss.item() / max_n_tokens

    return RunResult(accum_loss,
                     all_article_ids,
                     all_gold_sents,
                     all_gold_sents_with_number,
                     all_pred_sents,
                     all_pred_sents_with_number)
