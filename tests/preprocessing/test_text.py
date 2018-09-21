from unittest import TestCase
import tempfile

from janome.tokenizer import Tokenizer

from fag.preprocessing.text import (
    simplify_headline,
    is_template,
    replace_prices_with_tags,
    kansuuzi2number)
from fag.util.constant import IDEOGRAPHIC_SPACE


class TestPreprocessing(TestCase):

    def setUp(self):
        content = [
            ','.join([
                '日経平均',
                '1285',
                '1285',
                '5537',
                '名詞',
                '一般',
                '*',
                '*',
                '*',
                '*',
                '日経平均',
                'ニッケイヘイキン',
                'ニッケイヘイキン']),
            ','.join([
                '円安'
                '1285',
                '1285',
                '3534',
                '名詞',
                '一般',
                '*',
                '*',
                '*',
                '*',
                '円安',
                'エンヤス',
                'エンヤス'])
            ]
        with tempfile.NamedTemporaryFile(mode='w+t') as f:
            f.write('\n'.join(content) + '\n')
            f.seek(0)
            self.tokenizer = Tokenizer(f.name)
        self.tokenizer = Tokenizer('resources/user-dict.csv')

    def test_simplify_headline(self):

        s = '<NQN>◇＜東証＞三菱ＵＦＪが続伸　株高受けた買い戻し優勢'
        expected = '三菱UFJが続伸　株高受けた買い戻し優勢'
        self.assertEqual(simplify_headline(s), expected)

        s = IDEOGRAPHIC_SPACE.join([
            '日経平均、一時8600円下回る',
            'TOPIXは年初来安値下回る',
            '円高とｱｼﾞｱ株安で'])
        expected = IDEOGRAPHIC_SPACE.join([
            '日経平均、一時8600円下回る',
            'TOPIXは年初来安値下回る',
            '円高とアジア株安で'])
        self.assertEqual(simplify_headline(s), expected)

        s = '【要ﾁｪｯｸ画面】日銀追加緩和見送り'
        expected = '日銀追加緩和見送り'
        self.assertEqual(simplify_headline(s), expected)

    def test_is_template(self):

        true = '日経平均前引け、小反発　<yen val="100"/>高の<yen val="10000"/>'
        self.assertTrue(is_template(true))

        false = '日経平均前引け、反発　こんにちは'
        self.assertFalse(is_template(false))

    def test_replace_prices_with_tags(self):

        headline = '日経平均222円安、1500円割れ　円安一服で'
        tokens = self.tokenizer.tokenize(headline)
        tag_tokens = replace_prices_with_tags([t.surface for t in tokens])
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
        self.assertEqual(tag_tokens, expected)

    def test_kansuuzi2number(self):

        tokens = ['1', '万', '円', '台']
        expected = ['10000', '円', '台']
        self.assertEqual(kansuuzi2number(tokens), expected)

        tokens = ['賞金', 'は' '500', '万']
        expected = ['賞金', 'は' '500', '万']
        self.assertEqual(kansuuzi2number(tokens), expected)
