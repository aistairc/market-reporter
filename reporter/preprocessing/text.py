import os
import re
from typing import List

import mojimoji
from reporter.util.constant import IDEOGRAPHIC_SPACE


YEN_EXPRS = ['円', '円高', '円安']


def is_template(text: str) -> bool:
    """
    >>> is_template('日経平均前引け、続伸　100円高の12000円</s>')
    >>> True
    """

    start = r'(東証レビュー\([1-3]?[0-9]日\)( )?)?(日経平均)((前引け)|(大引け))?(、|　)'
    stock_change = r'([0-9]?日)?((小)|(大幅)|(小幅))?((続伸)|(続落)|(反発)|(反落))　'
    mention = r'(((前引け)|(大引け)|(終値)|(午前終値))は)?'
    stock_value = r'(<yen val=(.+?)\/>)(高|安)の(<yen val=(.+?)\/>)'
    template = start + stock_change + mention + stock_value
    return re.fullmatch(template, text) is not None


def simplify_headline(headline_text: str) -> str:
    """
    >>> simplify_headline('<NQN>◇＜東証＞三菱ＵＦＪが続伸　株高受けた買い戻し優勢')
    '三菱UFJが続伸　株高受けた買い戻し優勢'
    """
    PLACE_HOLDER = '<space/>'
    t = headline_text.strip().replace(IDEOGRAPHIC_SPACE, PLACE_HOLDER)
    t = mojimoji.han_to_zen(t, kana=True, digit=False, ascii=False)
    t = mojimoji.zen_to_han(t, kana=False, digit=True, ascii=True)
    t = re.sub('<\w+?>', '', t)
    t = re.sub('【\w+?】', '', t)

    return t.replace('◇', '') \
            .replace('◆', '') \
            .replace('◎', '') \
            .replace('☆', '') \
            .replace(PLACE_HOLDER, IDEOGRAPHIC_SPACE)


def kansuuzi2number(tokens: List[str]) -> List[str]:
    """
    >>> kansuuzi2number(['1', '万', '円', '台'])
    ['10000', '円', '台']
    >>> kansuuzi2number(['大引け', 'は', '147', '円', '高', 'の',
    ...                  '1', '万', '4000', '円'])
    ['大引け', 'は', '147', '円', '高', 'の', '14000', '円']
    """

    ts = tokens[:]
    n = len(ts)

    while '万' in ts:

        i = ts.index('万')

        if i == n - 1:
            break

        if tokens[i + 1] == '円':
            ts[i - 1] = ts[i - 1] + '0000'
            ts.pop(i)

        else:
            ts[i - 1] = ts[i - 1] + ts[i + 1].zfill(4)
            ts.pop(i + 1)
            ts.pop(i)

    return ts


def replace_prices_with_tags(tokens: List[str]) -> List[str]:
    """
    >>> replace_prices_with_tags(['大引け', 'は', '147', '円', '高', 'の',
    ...                           '14000', '円'])
    ['大引け', 'は', '<yen val="147"/>', '高', 'の', '<yen val="14000"/>']
    >>> replace_prices_with_tags(['高値', 'で', '終了'])
    ['高値', 'で', '終了']
    """

    ts = tokens[:]
    for i, t in enumerate(ts[:len(ts) - 1]):
        if t.isdigit() and ts[i + 1].startswith('円'):
            ts[i] = '<yen val="{}"/>'.format(t)
            if ts[i + 1] in YEN_EXPRS:
                ts[i + 1] = ts[i + 1].replace('円', '')
    return [t for t in ts if t != '']


def replace_tosho_with_n225(sentence: str) -> str:
    """
    >>> replace_tosho_with_n225('東証10時、小安い 円高や消費低迷が重荷')
    '日経平均、小安い 円高や消費低迷が重荷'
    """

    if sentence.startswith('東証10時') or sentence.startswith('東証14時'):
        return sentence.replace('10時', '') \
                       .replace('14時', '') \
                       .replace('東証', '日経平均')
    else:
        return sentence


def find_economic_exprs(headline: str) -> List[str]:
    """
    >>> find_economic_exprs('ユーロ高が原因で米株安')
    ['米株 安', 'ユーロ 高']
    """

    indices = ['円',
               '米株',
               '外株',
               '欧州株',
               '米国株',
               '中国株',
               '上海株',
               'アジア株',
               'ドル',
               'ユーロ',
               'ダウ',
               '先物']
    results = []
    for index in indices:
        expr = '{}(高|安)'.format(index)
        match = re.search(expr, headline)
        if match is not None:
            results.append(' '.join([index, match[1]]))
    return results


def list_csv_filenames(dirname: str) -> List[str]:
    results = []
    for filename in os.listdir(dirname):
        path = os.path.join(dirname, filename)
        if not os.path.isfile(path):
            continue
        ext = filename.lower().split('.')[-1]
        if ext not in ['gz', 'csv', 'tsv']:
            continue
        results.append(path)
    return results


def is_interesting(headline: str) -> bool:
    """
    >>> '日経平均続落'
    True
    """

    is_used = '日経平均' in headline or '東証' in headline
    is_used = is_used and '東証株価指数' not in headline
    is_used = is_used and 'ジャスダック' not in headline

    return is_used
