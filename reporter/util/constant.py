from enum import Enum, unique

import pytz

REUTERS_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f000%z'
NIKKEI_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S%z'
HEADLINE_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S %z'
POSTGRES_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S %z'

UTC = pytz.utc
JST = pytz.timezone('Asia/Tokyo')

EST = -5
EDT = -4

N_LONG_TERM = 7
N_SHORT_TERM = 62

TIMESLOT_SIZE = 24
GENERATION_LIMIT = 128

SEED = 0

IDEOGRAPHIC_SPACE = '\u3000'

EQUITY = 'EQTY'
FUTURES = 'DERV/FUT'
DOMESTIC_INDEX = '国内インデックス'


@unique
class Code(Enum):
    N225 = '.N225'
    SPX = '.SPX'
    TOPIX = '.TOPX'


@unique
class Phase(Enum):
    Train = 'train'
    Valid = 'valid'
    Test = 'test'


@unique
class SeqType(Enum):
    ArticleID = 'article_id'
    Time = 'time'
    Token = 'token'
    RawShort = 'raw_short'
    RawLong = 'raw_long'
    MovRefShort = 'moving_reference_short'
    MovRefLong = 'moving_reference_long'
    NormMovRefShort = 'normalized_moving_reference_short'
    NormMovRefLong = 'normalized_moving_reference_long'
    StdShort = 'standardized_short'
    StdLong = 'standardized_long'


@unique
class SpecialToken(Enum):
    BOS = '<s>'
    EOS = '</s>'
    Unknown = '<unk/>'
    Padding = '<pad/>'


@unique
class Category(Enum):
    NORMAL = ('<normal/>')
    STOCK_CURRENCY = ('<stock_currency/>')
    TEMPLATE = ('<template/>')

    def __new__(cls, value):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.id = len(cls.__members__)
        return obj


class Reuters:
    start = '2010-01-01T00:00:00.000Z'
    end = '2017-12-14T00:00:00.000Z'
    rest_api_root_uri = 'https://hosted.datascopeapi.reuters.com/RestApi/v1/'
    extraction_raw_uri = rest_api_root_uri + 'Extractions/ExtractRaw'
    raw_extraction_results_uri = \
        rest_api_root_uri + "Extractions/RawExtractionResults('{}')/$value"
    auth_token_uri = rest_api_root_uri + 'Authentication/RequestToken'
