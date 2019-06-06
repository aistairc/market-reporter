from datetime import datetime, timedelta
from itertools import groupby
from typing import Dict, Iterable, List, Tuple

from sqlalchemy import Date, cast
from sqlalchemy.orm.session import Session
from sqlalchemy.sql import text

from reporter.database.misc import in_jst
from reporter.database.model import Close, Price
from reporter.database.read import fetch_prices_of_a_day
from reporter.util.constant import UTC


def fetch_points(session: Session, ric: str, start: datetime, end: datetime) -> Tuple[List[int], List[str]]:

    ts = []
    ps = []
    t_prev_step = start

    for t, p in fetch_prices_of_a_day(session, ric, end):
        diff = t - t_prev_step
        if diff.seconds > 5 * 60:
            t_next_step = t_prev_step + timedelta(seconds=5 * 60)
            ts.append(t_next_step.astimezone(UTC))
            ps.append(None)
            while (t - t_next_step).seconds > 5 * 60:
                t_next_step += timedelta(seconds=5 * 60)
                ts.append(t_next_step.astimezone(UTC))
                ps.append(None)

        ts.append(t.astimezone(UTC))
        ps.append(str(p) if t <= end else None)

        t_prev_step = t

    return ts, ps


def _xs_ys_of_group(iter: Iterable[Tuple[float, float, float]]) -> Dict[str, List[float]]:
    result = {'xs': [], 'ys': []}
    for t, val, _ in iter:
        result['xs'].append(t)
        result['ys'].append(val)
    return result


def fetch_all_points_fast(session: Session, rics: List[str], start: datetime, end: datetime) -> Dict[str, float]:
    sql = text("""
               SELECT EXTRACT(epoch FROM t) AS t, val ::float, ric
               FROM
               (SELECT generate_series(:start ::timestamp, :end ::timestamp, '5 minutes' ::interval) AS t) times
               CROSS JOIN
               (SELECT * FROM (VALUES
               """ +
               ", ".join(["(:ric%d)" % i for i in range(len(rics))])
               + """
               ) AS ric_vals (ric)) rics
               NATURAL LEFT JOIN prices
               ORDER BY ric ASC, t ASC
               """)
    ric_dict = {"ric%d" % i: ric for i, ric in enumerate(rics)}
    result = session.bind.execute(sql, start=start, end=end, **ric_dict)
    result = {
        ric: _xs_ys_of_group(g) for ric, g in groupby(result, lambda e: e[2])
    }
    return result


def fetch_close(session: Session, ric: str, jst: datetime) -> float:
    result = session \
        .query(Price.val) \
        .filter(cast(in_jst(Close.t), Date) == jst.date(), Close.ric == ric, Close.t == Price.t, Price.ric == ric) \
        .scalar()
    return float(result) if result is not None else None


def fetch_all_closes_fast(session: Session, rics: List[str], start: datetime, end: datetime) -> Dict[str, float]:
    sql = text("""
               SELECT prices.ric, prices.val ::float
               FROM
               (SELECT * FROM (VALUES
               """ +
               ", ".join(["(:ric%d)" % i for i in range(len(rics))])
               + """
               ) AS ric_vals (ric)) rics
               NATURAL JOIN prices
               NATURAL LEFT JOIN closes
               WHERE closes.t >= :start AND closes.t < :end
               """)
    ric_dict = {"ric%d" % i: ric for i, ric in enumerate(rics)}
    result = session.bind.execute(sql, start=start, end=end, **ric_dict)
    result = dict(list(result))
    return result
