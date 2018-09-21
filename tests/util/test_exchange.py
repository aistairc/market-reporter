from pathlib import Path
from unittest import TestCase
from datetime import time
import pytz

from fag.util.constant import EST, EDT
from fag.util.exchange import ClosingTime


class TestClosingTime(TestCase):

    def setUp(self):
        dir_resources = Path('resources')
        self.ct = ClosingTime(dir_resources)

    def test_func_get_close_t_tse(self):
        TOKYO_STOCK_EXCHANGE = 'TSE'
        get_close_t_tse = self.ct.func_get_close_t(TOKYO_STOCK_EXCHANGE)
        tse_close_t = get_close_t_tse(None)
        self.assertEqual(tse_close_t, time(6, 0, tzinfo=pytz.UTC))

    def test_func_get_close_t_nyse(self):
        NEW_YORK_STOCK_EXCHANGE = 'NYSE'
        get_close_t_nyse = self.ct.func_get_close_t(NEW_YORK_STOCK_EXCHANGE)
        nyse_close_t = get_close_t_nyse(EST)
        self.assertEqual(nyse_close_t, time(21, 0, tzinfo=pytz.UTC))

    def test_func_get_close_t_dst(self):
        # daylight saving time
        NEW_YORK_STOCK_EXCHANGE = 'NYSE'
        get_close_t_nyse = self.ct.func_get_close_t(NEW_YORK_STOCK_EXCHANGE)
        nyse_close_t = get_close_t_nyse(EDT)
        self.assertEqual(nyse_close_t, time(20, 0, tzinfo=pytz.UTC))

    def test_func_get_close_t_osa(self):
        OSAKA_STOCK_EXCHANGE = 'OSA'
        get_close_t_osa = self.ct.func_get_close_t(OSAKA_STOCK_EXCHANGE)
        tse_close_t = get_close_t_osa(None)
        self.assertEqual(tse_close_t, time(20, 30, tzinfo=pytz.UTC))
