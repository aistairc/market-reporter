from janome.tokenizer import Tokenizer

from reporter.preprocessing.text import (
    is_template,
    kansuuzi2number,
    replace_prices_with_tags,
    simplify_headline
)
from reporter.util.constant import IDEOGRAPHIC_SPACE


def test_simplify_headline():

    s = '<NQN>◇＜東証＞三菱ＵＦＪが続伸　株高受けた買い戻し優勢'
    expected = '三菱UFJが続伸　株高受けた買い戻し優勢'
    result = simplify_headline(s)
    assert result == expected

    s = IDEOGRAPHIC_SPACE.join([
        '日経平均、一時8600円下回る',
        'TOPIXは年初来安値下回る',
        '円高とｱｼﾞｱ株安で'])
    expected = IDEOGRAPHIC_SPACE.join([
        '日経平均、一時8600円下回る',
        'TOPIXは年初来安値下回る',
        '円高とアジア株安で'])
    result = simplify_headline(s)
    assert result == expected

    s = '【要ﾁｪｯｸ画面】日銀追加緩和見送り'
    expected = '日銀追加緩和見送り'
    result = simplify_headline(s)
    assert result == expected


def test_is_template():

    t = '日経平均前引け、小反発　100円高の10000円'
    assert is_template(t)


def test_is_not_template():

    t = '日経平均前引け、反発　こんにちは'
    assert not is_template(t)


def test_replace_prices_with_tags():

    tokenizer = Tokenizer('resources/user-dict.csv')

    headline = '日経平均222円安、1500円割れ　円安一服で'
    tokens = tokenizer.tokenize(headline)
    result = replace_prices_with_tags([t.surface for t in tokens])
    expected = ['日経平均',
                '<yen val="222"/>',
                '安',
                '、',
                '<yen val="1500"/>',
                '割れ',
                IDEOGRAPHIC_SPACE,
                '円安',
                '一服',
                'で']
    assert result == expected


def test_kansuuzi2number():

    tokens = ['1', '万', '円', '台']
    expected = ['10000', '円', '台']
    result = kansuuzi2number(tokens)
    assert result == expected

    tokens = ['賞金', 'は' '500', '万']
    expected = ['賞金', 'は' '500', '万']
    result = kansuuzi2number(tokens)
    assert result == expected
