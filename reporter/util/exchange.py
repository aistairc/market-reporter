import json
from datetime import datetime, time
from pathlib import Path
from typing import Callable

from pytz import UTC


def convert_24h_to_12h(h: int) -> int:
    return h if h < 23 else h - 24


class ClosingTime:

    def __init__(self, dir_resources: Path):
        self.dir_resources = dir_resources
        dest_se_info = self.dir_resources / Path('stock-exchanges.json')
        with dest_se_info.open(mode='r') as f:
            self.se_info = json.load(f)

        dest_ric = self.dir_resources / Path('ric.csv')
        with dest_ric.open(mode='r') as f:
            self.ric_se_pairs = [(line[0], line[4]) for line in f.readlines()[1:]]

        self.ric2tz = \
            dict([(ric, self.se_info.get(name_of_stock_exchange, {}).get('tz', 'UTC'))
                  for (ric, name_of_stock_exchange) in self.ric_se_pairs])

    def convert_24h_to_12h(self, h: int) -> int:
        return h if h < 23 else h - 24

    def func_get_close_t(self, stock_exchange: str) -> Callable[[time], time]:

        this_se_info = self.se_info[stock_exchange]
        utc_offset = int(this_se_info['utc_offset'])
        if utc_offset >= 0:
            s_utc_offset = '+' + '{:02d}00'.format(utc_offset)
        else:
            s_utc_offset = '{:03d}00'.format(utc_offset)
        h, m = this_se_info['close_local'].split(':')
        template = '2000-01-01 {:02d}:{:02d}:00{}'
        close_local = datetime.strptime(template.format(convert_24h_to_12h(int(h)), int(m), s_utc_offset),
                                        '%Y-%m-%d %H:%M:%S%z')
        close_t = close_local.astimezone(UTC)
        has_dst = this_se_info['has_dst']

        def _f(_: None) -> time:
            return time(hour=close_t.hour, minute=close_t.minute, tzinfo=UTC)

        def _f_dst(_utc_offset: int) -> time:

            if int(_utc_offset) == int(utc_offset):
                return time(close_t.hour, close_t.minute, tzinfo=UTC)
            else:
                return time(close_t.hour - 1, close_t.minute, tzinfo=UTC)

        if has_dst:
            return _f_dst
        else:
            return _f
