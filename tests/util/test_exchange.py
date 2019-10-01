from datetime import time
from pathlib import Path

import pytz

from reporter.util.constant import EDT, EST
from reporter.util.exchange import ClosingTime


def test_func_get_close_t_tse():
    dir_resources = Path('resources')
    ct = ClosingTime(dir_resources)

    TOKYO_STOCK_EXCHANGE = 'TSE'
    OSAKA_STOCK_EXCHANGE = 'OSA'
    NEW_YORK_STOCK_EXCHANGE = 'NYSE'

    get_close_t_tse = ct.func_get_close_t(TOKYO_STOCK_EXCHANGE)
    tse_close_t = get_close_t_tse(None)
    assert tse_close_t == time(6, 0, tzinfo=pytz.UTC)

    # standard time
    get_close_t_nyse = ct.func_get_close_t(NEW_YORK_STOCK_EXCHANGE)
    nyse_close_t = get_close_t_nyse(EST)
    assert nyse_close_t == time(21, 0, tzinfo=pytz.UTC)

    # daylight saving time
    get_close_t_nyse = ct.func_get_close_t(NEW_YORK_STOCK_EXCHANGE)
    nyse_close_edt_t = get_close_t_nyse(EDT)
    assert nyse_close_edt_t == time(20, 0, tzinfo=pytz.UTC)

    get_close_t_osa = ct.func_get_close_t(OSAKA_STOCK_EXCHANGE)
    tse_close_t = get_close_t_osa(None)
    assert tse_close_t == time(20, 30, tzinfo=pytz.UTC)
