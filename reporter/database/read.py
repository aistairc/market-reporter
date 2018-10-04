import itertools
from datetime import datetime, timedelta
from decimal import Decimal
from logging import Logger
from typing import Any, Dict, List, Tuple
from xml.etree.ElementTree import fromstring

import numpy
from redis import Redis
from sqlalchemy import Integer, cast, extract, func, Date
from sqlalchemy.orm import Session
from tqdm import tqdm

from reporter.core.operation import find_operation
from reporter.database.misc import in_utc, in_jst
from reporter.database.model import Headline, Price
from reporter.util.constant import REUTERS_DATETIME_FORMAT, Code, Phase, SeqType, UTC
from reporter.util.conversion import stringify_ric_seqtype


class Alignment:

    def __init__(self,
                 article_id: str,
                 t: str,
                 jst_hour: int,
                 processed_tokens: List[str],
                 chart: Dict[str, List[str]]):

        self.article_id = article_id
        self.t = t
        self.jst_hour = jst_hour
        self.processed_tokens = processed_tokens
        self.chart = chart

    def to_mapping(self) -> Dict[str, Any]:
        return {'article_id': self.article_id,
                't': self.t,
                'jst_hour': self.jst_hour,
                'processed_tokens': self.processed_tokens,
                **self.chart}


def are_headlines_ready(session: Session):

    return session \
        .query(Headline) \
        .filter(Headline.headline.isnot(None)) \
        .first() is not None


def fetch_rics(session: Session) -> List[str]:
    results = session.query(Price.ric).distinct()
    return [result.ric for result in results]


def fetch_date_range(session: Session) -> Tuple[datetime, datetime]:
    results = session.query(func.min(Price.t), func.max(Price.t)).first()
    return results


def fetch_prices_of_a_day(session: Session,
                          ric: str,
                          jst: datetime) -> List[Tuple[datetime, Decimal]]:
    results = session \
        .query(func.to_char(in_utc(Price.t), 'YYYY-MM-DD HH24:MI:SS').label('t'),
               Price.val) \
        .filter(cast(in_jst(Price.t), Date) == jst.date(), Price.ric == ric) \
        .order_by(Price.t) \
        .all()

    return [(datetime.strptime(r.t, '%Y-%m-%d %H:%M:%S').replace(tzinfo=UTC), r.val)
            for r in results]


def fetch_max_t_of_prev_trading_day(session: Session, ric: str, t: datetime) -> int:

    assert(t.tzinfo == UTC)

    prev_day = t + timedelta(hours=9) - timedelta(days=1)

    return session \
        .query(extract('epoch', func.max(Price.t))) \
        .filter(cast(in_jst(Price.t), Date) <= prev_day.date(), Price.ric == ric) \
        .scalar()


def load_alignments_from_db(session: Session, r: Redis, phase: Phase, logger: Logger) -> List[Alignment]:

    headlines = session \
        .query(Headline.article_id,
               Headline.tag_tokens,
               Headline.t,
               cast(extract('epoch', Headline.t), Integer).label('unixtime'),
               cast(extract('hour', in_jst(Headline.t)), Integer).label('jst_hour')) \
        .filter(Headline.is_used.is_(True), Headline.phase == phase.value) \
        .order_by(Headline.t) \
        .all()
    headlines = list(headlines)

    rics = fetch_rics(session)

    alignments = []
    seqtypes = [SeqType.RawShort, SeqType.RawLong,
                SeqType.MovRefShort, SeqType.MovRefLong,
                SeqType.NormMovRefShort, SeqType.NormMovRefLong,
                SeqType.StdShort, SeqType.StdLong]
    logger.info('start creating alignments between headlines and price sequences.')

    ric_seqtype_to_keys = dict()
    ric_seqtype_to_unixtimes = dict()
    for (ric, seqtype) in itertools.product(rics, seqtypes):
        ric_seqtype_to_keys[(ric, seqtype)] = \
            [k for k in r.keys(ric + '__' + seqtype.value + '__*')]
        ric_seqtype_to_unixtimes[(ric, seqtype)] = \
            numpy.array([datetime.strptime(k.split('__')[2], REUTERS_DATETIME_FORMAT).timestamp()
                         for k in ric_seqtype_to_keys[(ric, seqtype)]], dtype=numpy.int64)
    for h in tqdm(headlines):

        # Find the latest prices before the article is published
        chart = dict()
        for (ric, seqtype) in itertools.product(rics, seqtypes):
            U = ric_seqtype_to_unixtimes[(ric, seqtype)]
            # Find the latest sequence before the headline is published
            valid_indices = numpy.where(U <= h.unixtime)
            if valid_indices[0].shape[0] == 0:
                vals = []
            else:
                i_max_sub = U[valid_indices].argmax()
                i_max = numpy.arange(U.shape[0])[valid_indices][i_max_sub]
                key = ric_seqtype_to_keys[(ric, seqtype)][i_max]
                vals = r.lrange(key, 0, -1)
                # TODO
                # if seqtype.value.endswith('short') and len(vals) > N_SHORT_TERM:
                #     vals = vals[:N_SHORT_TERM]
                # elif seqtype.value.endswith('long') and len(vals) > N_LONG_TERM:
                #     vals = vals[:N_LONG_TERM]
            chart[stringify_ric_seqtype(ric, seqtype)] = vals

        # Replace tags with price tags
        tag_tokens = h.tag_tokens

        short_term_vals = chart[stringify_ric_seqtype(Code.N225.value, SeqType.RawShort)]
        long_term_vals = chart[stringify_ric_seqtype(Code.N225.value, SeqType.RawLong)]

        processed_tokens = []
        for i in range(len(tag_tokens)):
            t = tag_tokens[i]
            if t.startswith('<yen val="') and t.endswith('"/>'):
                ref = fromstring(t).attrib['val']

                if len(short_term_vals) > 0 and len(long_term_vals) > 0:

                    prev_trading_day_close = Decimal(long_term_vals[0])
                    latest = Decimal(short_term_vals[0])
                    p = find_operation(ref, prev_trading_day_close, latest)
                    processed_tokens.append(p)
                else:
                    processed_tokens.append('<yen val="z"/>')
            else:
                processed_tokens.append(tag_tokens[i])

        alignment = Alignment(h.article_id, str(h.t), h.jst_hour, processed_tokens, chart)
        alignments.append(alignment.to_mapping())
    logger.info('end creating alignments between headlines and price sequences.')
    return alignments
