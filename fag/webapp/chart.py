from typing import List, Tuple
from datetime import datetime, timedelta

from sqlalchemy.orm.session import Session

from fag.database.read import fetch_prices_of_a_day
from fag.util.constant import UTC


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
