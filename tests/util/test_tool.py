from types import GeneratorType
from unittest import TestCase

from reporter.util.tool import takeuntil


class TestTool(TestCase):

    def test_takeuntil(self):
        result = list(takeuntil('</s>', ['Nikkei', 'rises', '</s>', '</s>']))
        self.assertEqual(result, ['Nikkei', 'rises', '</s>'])

    def test_takeuntil_is_generator(self):
        result = takeuntil('</s>', ['Nikkei', 'rises', '</s>', '</s>'])
        self.assertIsInstance(result, GeneratorType)

    def test_takeuntil_missing(self):
        s = ['Dream', 'Theater', 'is', 'one', 'of', 'the', 'greatest', 'bands']
        result = list(takeuntil('a', s))
        self.assertEqual(result, s)
