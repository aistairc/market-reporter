from unittest import TestCase

from fag.postprocessing.text import number2kansuuzi


class TestPostprocessing(TestCase):

    def test_number2kansuuzi(self):
        s = ['大引け', 'は', '147', '円', '高', 'の', '14000円']
        expected = ['大引け', 'は', '147', '円', '高', 'の', '1万4000円']
        self.assertEqual(number2kansuuzi(s), expected)

        s = ['10000円', '台']
        expected = ['1万円', '台']
        self.assertEqual(number2kansuuzi(s), expected)
