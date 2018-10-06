import csv
import gzip
from datetime import datetime
from decimal import Decimal
from logging import Logger
from math import isclose
from pathlib import Path
from typing import List

import pandas
from janome.tokenizer import Tokenizer
from pytz import UTC
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import extract
from tqdm import tqdm

from reporter.database.misc import in_jst
from reporter.database.model import Close, Headline, Instrument, Price, PriceSeq
from reporter.preprocessing.text import (
    is_interesting,
    is_template,
    kansuuzi2number,
    replace_prices_with_tags,
    simplify_headline)
from reporter.resource.reuters import ric2filename
from reporter.util.config import Span
from reporter.util.constant import (
    DOMESTIC_INDEX,
    EQUITY,
    FUTURES,
    JST,
    N_LONG_TERM,
    N_SHORT_TERM,
    NIKKEI_DATETIME_FORMAT,
    REUTERS_DATETIME_FORMAT,
    Code,
    Phase,
    SeqType)
from reporter.util.exchange import ClosingTime


def insert_prices(session: Session,
                  dir_prices: Path,
                  missing_rics: List[str],
                  dir_resources: Path,
                  logger: Logger) -> None:

    ct = ClosingTime(dir_resources)
    insert_instruments(session, dir_resources / Path('ric.csv'), logger)
    seqtypes = [SeqType.RawShort, SeqType.RawLong,
                SeqType.MovRefShort, SeqType.MovRefLong,
                SeqType.NormMovRefShort, SeqType.NormMovRefLong,
                SeqType.StdShort, SeqType.StdLong]

    for ric in missing_rics:

        filename = ric2filename(dir_resources / Path('prices'), ric, extension='csv.gz')

        price_seqs = dict((seqtype, []) for seqtype in seqtypes)
        with gzip.open(filename, mode='rt') as f:
            dataframe = pandas.read_table(f, delimiter=',')
            column = 'Close Bid' if int(dataframe[['Last']].dropna().count()) == 0 else 'Last'
            mean = Decimal(float(dataframe[[column]].mean()))
            std = Decimal(float(dataframe[[column]].std()))

            f.seek(0)
            N = sum(1 for _ in f) - 1

            f.seek(0)
            reader = csv.reader(f, delimiter=',')
            next(reader)
            fields = next(reader)
            ric = fields[0]

            stock_exchange = session \
                .query(Instrument.exchange) \
                .filter(Instrument.ric == ric) \
                .scalar()
            if stock_exchange is None:
                stock_exchange = 'TSE'
            get_close_utc = ct.func_get_close_t(stock_exchange)

            logger.info('start importing {}'.format(f.name))

            f.seek(0)
            column_names = next(reader)
            # Some indices contain an additional column
            shift = 1 if column_names[1] == 'Alias Underlying RIC' else 0

            prices = []
            close_prices = []
            raw_short_vals = []
            raw_long_vals = []
            raw_mov_ref_long_vals = []
            raw_mov_ref_short_vals = []
            std_long_vals = []
            std_short_vals = []
            prev_row_t = None
            max_mov_ref_long_val = Decimal('-Infinity')
            min_mov_ref_long_val = Decimal('Infinity')
            max_mov_ref_short_val = Decimal('-Infinity')
            min_mov_ref_short_val = Decimal('Infinity')

            for _ in tqdm(range(N)):
                fields = next(reader)

                ric = fields[0]
                t = fields[2 + shift].replace('Z', '+0000')
                utc_offset = int(fields[3 + shift])
                if ric == Code.SPX.value:
                    utc_offset += 1
                last = fields[8 + shift].strip()
                close_bid = fields[14 + shift].strip()

                if last == '' and close_bid == '':
                    continue
                val = Decimal(close_bid if last == '' else last)
                std_val = (val - mean) / std
                try:
                    t = datetime.strptime(t, REUTERS_DATETIME_FORMAT)
                except ValueError:
                    logger.info('ValueError: {}, {}, {}'.format(ric, t, val))
                    continue

                if prev_row_t is not None:

                    if prev_row_t == t:
                        continue

                    close_time = get_close_utc(utc_offset)
                    close_datetime = datetime(t.year, t.month, t.day,
                                              close_time.hour, close_time.minute,
                                              tzinfo=UTC)

                    if prev_row_t < close_datetime and close_datetime <= t:
                        close_prices.append(Close(ric, t).to_dict())

                        if len(raw_long_vals) > 1:
                            raw_mov_ref_long_val = val - raw_long_vals[0]
                            raw_mov_ref_long_vals = [raw_mov_ref_long_val] + raw_mov_ref_long_vals \
                                if len(raw_mov_ref_long_vals) < N_LONG_TERM \
                                else [raw_mov_ref_long_val] + raw_mov_ref_long_vals[:-1]
                            price_seqs[SeqType.MovRefLong] \
                                .append(PriceSeq(ric, SeqType.MovRefLong, t, raw_mov_ref_long_vals).to_dict())
                            max_mov_ref_long_val = float(raw_mov_ref_long_val) \
                                if raw_mov_ref_long_val > max_mov_ref_long_val \
                                else float(max_mov_ref_long_val)
                            min_mov_ref_long_val = float(raw_mov_ref_long_val) \
                                if raw_mov_ref_long_val < min_mov_ref_long_val \
                                else float(min_mov_ref_long_val)

                        raw_long_vals = [val] + raw_long_vals \
                            if len(raw_long_vals) < N_LONG_TERM \
                            else [val] + raw_long_vals[:-1]
                        price_seqs[SeqType.RawLong] \
                            .append(PriceSeq(ric, SeqType.RawLong, t, raw_long_vals).to_dict())
                        price_seqs[SeqType.RawLong]. \
                            append(PriceSeq(ric, SeqType.RawLong, t, raw_long_vals).to_dict())

                        std_long_vals = [std_val] + std_long_vals \
                            if len(std_long_vals) < N_LONG_TERM \
                            else [std_val] + std_long_vals[:-1]
                        price_seqs[SeqType.StdLong] \
                            .append(PriceSeq(ric, SeqType.StdLong, t, std_long_vals).to_dict())

                prices.append(Price(ric, t, utc_offset, val).to_dict())

                if len(raw_short_vals) > 1 and len(raw_long_vals) > 2:
                    raw_mov_ref_short_val = val - raw_long_vals[1 if t == close_datetime else 0]
                    raw_mov_ref_short_vals = [raw_mov_ref_short_val] + raw_mov_ref_short_vals \
                        if len(raw_mov_ref_short_vals) < N_SHORT_TERM \
                        else [raw_mov_ref_short_val] + raw_mov_ref_short_vals[:-1]
                    price_seqs[SeqType.MovRefShort] \
                        .append(PriceSeq(ric, SeqType.MovRefShort, t, raw_mov_ref_short_vals).to_dict())
                    max_mov_ref_short_val = float(raw_mov_ref_short_val) \
                        if raw_mov_ref_short_val > max_mov_ref_short_val \
                        else float(max_mov_ref_short_val)
                    min_mov_ref_short_val = float(raw_mov_ref_short_val) \
                        if raw_mov_ref_short_val < min_mov_ref_short_val \
                        else float(min_mov_ref_short_val)

                raw_short_vals = [val] + raw_short_vals \
                    if len(raw_short_vals) < N_SHORT_TERM \
                    else [val] + raw_short_vals[:-1]
                price_seqs[SeqType.RawShort] \
                    .append(PriceSeq(ric, SeqType.RawShort, t, raw_short_vals).to_dict())

                std_short_vals = [std_val] + std_short_vals \
                    if len(std_short_vals) < N_SHORT_TERM \
                    else [std_val] + std_short_vals[:-1]
                price_seqs[SeqType.StdShort] \
                    .append(Price(ric, SeqType.StdShort, t, std_short_vals).to_dict())
                prev_row_t = t

            session.execute(Price.__table__.insert(), prices)
            session.execute(Close.__table__.insert(), close_prices)

            for seqtype in seqtypes:
                if seqtype == SeqType.NormMovRefLong:
                    price_seqs[seqtype] = \
                        [PriceSeq(ric, p['t'], SeqType.NomMovRefLong, None)
                         for p in price_seqs[SeqType.MovRefLong]] \
                        if isclose(max_mov_ref_long_val, min_mov_ref_long_val) \
                        else [PriceSeq(ric, p['t'], SeqType.NormMovRefLong,
                                       [(2 * v - (max_mov_ref_long_val + min_mov_ref_long_val)) /
                                        (max_mov_ref_long_val - min_mov_ref_long_val)
                                        for v in p['vals']]).to_dict()
                              for p in price_seqs[SeqType.MovRefLong]]
                session.execute(PriceSeq.__table__.insert(), price_seqs[seqtype])
            session.commit()

            logger.info('end importing {}'.format(ric))


def insert_headlines(session: Session,
                     dir_nikkei_headline: Path,
                     train_span: Span,
                     valid_span: Span,
                     test_span: Span,
                     logger: Logger) -> None:

    dests = list(dir_nikkei_headline.glob('*.csv.gz')) + list(dir_nikkei_headline.glob('*.csv'))
    for dest in dests:
        with gzip.open(str(dest), mode='rt') if dest.suffix == '.gz' else dest.open(mode='r') as f:

            N = sum(1 for _ in f) - 1
            f.seek(0)
            reader = csv.reader(f, delimiter=',', quoting=csv.QUOTE_ALL)
            next(reader)
            fields = next(reader)
            t = fields[1]
            if 'Z' not in t or '+' not in t:
                t = t + '+0000'
            t = datetime.strptime(t, NIKKEI_DATETIME_FORMAT).astimezone(JST)
            first = session \
                .query(Headline) \
                .filter(extract('year', in_jst(Headline.t)) == t.year) \
                .first()
            if first is not None:
                return

            logger.info('start {}'.format(f.name))

            f.seek(0)
            next(reader)
            headlines = []
            for _ in tqdm(range(N)):
                fields = next(reader)
                t = fields[1]
                if 'Z' not in t or '+' not in t:
                    t = t + '+0000'
                article_id = fields[5]
                headline = fields[6]
                isins = None if fields[25] == '' else fields[25].split(':')
                countries = None if fields[36] == '' else fields[36].split(':')
                categories = None if fields[37] == '' else fields[37].split(':')
                keywords_headline = None if fields[-2] == '' else fields[-2].split(':')
                keywords_article = None if fields[-1] == '' else fields[-1].split(':')
                try:
                    t = datetime.strptime(t, NIKKEI_DATETIME_FORMAT)
                except ValueError:
                    message = 'ValueError: {}, {}, {}'
                    logger.info(message.format(t, article_id, headline))
                    continue

                if train_span.start <= t and t < train_span.end:
                    phase = Phase.Train.value
                elif valid_span.start <= t and t < valid_span.end:
                    phase = Phase.Valid.value
                elif test_span.start <= t and t < test_span.end:
                    phase = Phase.Test.value
                else:
                    phase = None

                headlines.append({'article_id': article_id,
                                  't': t,
                                  'headline': headline,
                                  'isins': isins,
                                  'countries': countries,
                                  'categories': categories,
                                  'keywords_headline': keywords_headline,
                                  'keywords_article': keywords_article,
                                  'is_used': None,
                                  'phase': phase})

            session.execute(Headline.__table__.insert(), headlines)
            session.commit()


def update_headlines(session: Session, user_dict: Path, logger: Logger) -> None:

    query_result = session \
        .query(Headline) \
        .filter(Headline.is_used.is_(None)) \
        .all()
    headlines = list(query_result)

    if len(headlines) == 0:
        return

    tokenizer = Tokenizer(str(user_dict))
    mappings = []

    logger.info('start updating headlines')
    for headline in tqdm(headlines):

        h = simplify_headline(headline.headline)

        is_about_di = headline.categories is not None and \
            DOMESTIC_INDEX in headline.categories

        if is_template(h) or not is_interesting(h) or not is_about_di:
            mappings.append({
                'article_id': headline.article_id,
                'is_used': False
            })
            continue

        tokens = kansuuzi2number([token.surface
                                  for token in tokenizer.tokenize(h)])
        tag_tokens = replace_prices_with_tags(tokens)

        mappings.append({
            'article_id': headline.article_id,
            'simple_headline': h,
            'tokens': tokens,
            'tag_tokens': tag_tokens,
            'is_used': True,
        })
    session.bulk_update_mappings(Headline, mappings)
    session.commit()
    logger.info('end updating headlines')


def insert_instruments(session: Session, dest_ric: Path, logger: Logger) -> None:
    with dest_ric.open(mode='r') as f:
        reader = csv.reader(f, delimiter=',')
        next(reader)
        for fields in reader:
            ric = fields[0]
            desc = fields[1]
            currency = fields[2]
            type_ = fields[3]
            exchange = fields[4] if type_ in [EQUITY, FUTURES] else None
            instrument = Instrument(ric, desc, currency, type_, exchange)
            session.merge(instrument)
    session.commit()
