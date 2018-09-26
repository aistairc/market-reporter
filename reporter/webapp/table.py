import csv
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple, Union

from sqlalchemy.orm.session import Session

from reporter.database.model import Close, Price


class RICInfo:

    def __init__(self,
                 description: str,
                 currency: str,
                 utc_offset: int,
                 has_dst: bool):
        self.description = description
        self.currency = currency
        self.utc_offset = utc_offset
        self.has_dst = has_dst


class Table:

    def __init__(self,
                 ric: str,
                 description: str,
                 currency: str,
                 rows: List[Tuple[str, str, str]],
                 is_dummy: Union[bool, None] = False):

        self.ric = ric
        self.description = description
        self.currency = currency
        self.rows = rows
        self.is_dummy = is_dummy


def load_ric_to_ric_info() -> Dict[str, RICInfo]:
    with Path('resources', 'stock-exchanges.json').open(mode='r') as f:
        stock_exchange = json.load(f)
    result = {}
    with Path('resources', 'ric.csv').open(mode='r') as f:
        reader = csv.reader(f)
        next(reader)
        for line in reader:
            ric, desc, cur, _, exchange, _ = line
            exchange_info = stock_exchange.get(exchange, {})
            utc_offset = int(exchange_info.get('utc_offset', 0))
            has_dst = bool(exchange_info.get('has_dst'))
            result[ric] = RICInfo(desc, cur, utc_offset, has_dst)
    return result


def create_ric_tables(session: Session,
                      rics: List[str],
                      ric_to_ric_info: Dict[str, RICInfo],
                      timestamp: datetime) -> List[Table]:

    DATETIME_FORMAT = '%Y-%m-%d %H:%M'
    EPSILON = 1e-2
    n_days = 5

    tables = []
    for ric in rics:
        ric_info = ric_to_ric_info.get(ric)
        results = session \
            .query(Close.t, Price.val) \
            .join(Price, Close.t == Price.t) \
            .filter(Close.ric == ric, Close.ric == Price.ric, Close.t <= timestamp) \
            .order_by(Close.t.desc()) \
            .limit(n_days) \
            .all()
        prev_vals = [v for (_, v) in results][1:] + [Decimal(0)]
        formatted_rows = []
        for i, (t, v, diff) in enumerate([(t, v, v - prev_v) for ((t, v), prev_v)
                                          in zip(results, prev_vals)]):

            if i == len(results) - 1:
                indicator = '-'
            elif abs(diff) < EPSILON:
                indicator = '→'
            elif diff > 0:
                indicator = '↑'
            else:
                indicator = '↓'
            formatted_rows.append((t.strftime(DATETIME_FORMAT), '{:,.2f}'.format(v), indicator))

        table = Table(ric,
                      ric_info.description,
                      ric_info.currency,
                      formatted_rows)
        tables.append(table)

    return tables
