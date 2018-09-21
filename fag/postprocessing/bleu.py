from typing import List

from nltk.translate.bleu_score import SmoothingFunction, corpus_bleu


def calc_bleu(gold_sents: List[List[str]], pred_sents: List[List[str]]) -> float:

    list_of_references = [[sent] for sent in gold_sents]
    return corpus_bleu(list_of_references, pred_sents, smoothing_function=SmoothingFunction().method1)
