import re
from typing import List

from reporter.util.constant import SpecialToken


def number2kansuuzi(tokens: List[str]) -> List[str]:
    """
    >>> number2kansuuzi(['大引け', 'は', '147円', '高', 'の', '14000円'])
    ['大引け', 'は', '147円', '高', 'の', '1万4000円']
    >>> number2kansuuzi(['10000円', '台'])
    ['1万円', '台']
    """
    def convert(token: str) -> str:
        if re.match(r'\d{5,8}円', token) is None:
            return token
        else:
            major_part = token[:-5]
            minor_part = token[-5:-1]
            return '{}万円'.format(major_part) \
                if int(minor_part) == 0 \
                else '{}万{}円'.format(major_part, minor_part)

    return [convert(token) for token in tokens]


def remove_bos(sentence: List[str]) -> List[str]:
    """
    >>> remove_bos(['<s>', '日経平均', '、', '続落', 'で', '始まる', '</s>'])
    ['日経平均', '、', '続落', 'で', '始まる', '</s>']
    >>> remove_bos([])
    []
    """
    return sentence[1:] if len(sentence) > 0 and sentence[0] == SpecialToken.BOS.value else sentence
