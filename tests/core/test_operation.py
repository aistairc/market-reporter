from unittest import TestCase

from fag.core.operation import find_operation, perform_operation


class TestOperation(TestCase):

    def test_find_operation(self):

        ref_token = 100
        prev_trading_day_close = 10000
        latest = 10120
        result = find_operation(ref_token, prev_trading_day_close, latest)
        self.assertEqual(result, '<yen val="Δ-round-down-100"/>')

    def test_find_operation_reverse(self):

        ref_token = 100
        prev_trading_day_close = 10120
        latest = 10000
        result = find_operation(ref_token, prev_trading_day_close, latest)
        self.assertEqual(result, '<yen val="Δ-round-down-100"/>')

    def test_perform_operation(self):

        token = '<yen val="Δ-round-down-100"/>'
        prev_trading_day_close = 10000
        latest = 10120
        result = perform_operation(token, prev_trading_day_close, latest)
        self.assertEqual(result, '100円')
