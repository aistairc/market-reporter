import argparse
import itertools
from typing import List, Tuple
from datetime import datetime
from pathlib import Path

import numpy
import jsonlines
import torch
from torchtext.data import Field, Iterator, RawField, TabularDataset
from torchtext.vocab import Vocab
import redis
from redis import Redis

from reporter.database.read import Alignment
from reporter.util.config import Config
from reporter.util.constant import (
    N_LONG_TERM,
    N_SHORT_TERM,
    REUTERS_DATETIME_FORMAT,
    SeqType,
    SpecialToken)
from reporter.util.conversion import stringify_ric_seqtype


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog='reporter.predict')
    parser.add_argument('--device',
                        type=str,
                        metavar='DEVICE',
                        default='cpu',
                        help='`cuda:n` where `n` is an integer, or `cpu`')
    parser.add_argument('--config',
                        type=str,
                        dest='dest_config',
                        metavar='FILENAME',
                        default='config.toml',
                        help='specify config file (default: `config.toml`)')
    parser.add_argument('-m',
                        '--model',
                        type=str,
                        metavar='FILENAME')
    parser.add_argument('-t',
                        '--time',
                        type=str)
    parser.add_argument('--ric',
                        type=str)

    return parser.parse_args()


def predict() -> List[str]:

    args = parse_args()

    config = Config(args.dest_config)

    device = torch.device(args.device)

    dest_t = args.time
    dest_t = '2016-09-27T10:10:00.000000000+0900'
    dest_ric = args.ric

    # Connect to Redis
    connection_pool = redis.ConnectionPool(**config.redis)
    redis_client = redis.StrictRedis(connection_pool=connection_pool)

    # Make the alignment of predict
    rics = config.rics if dest_ric in config.rics else [dest_ric] + config.rics

    seqtypes = [SeqType.RawShort, SeqType.RawLong,
                SeqType.MovRefShort, SeqType.MovRefLong,
                SeqType.NormMovRefShort, SeqType.NormMovRefLong,
                SeqType.StdShort, SeqType.StdLong]

    alignment = load_alignment_from_db(redis_client, rics, dest_t, seqtypes)

    # Write the predict data
    config.dir_output.mkdir(parents=True, exist_ok=True)
    dest_alignment = config.dir_output / Path('alignment-predict.json')
    with dest_alignment.open(mode='w') as f:
        writer = jsonlines.Writer(f)
        writer.write(alignment.to_mapping())

    (vocab, predict_iter) = create_dataset(config, device, rics, seqtypes)


def load_alignment_from_db(r: Redis,
                           rics: List[str],
                           t: str,
                           seqtypes: List[SeqType]) -> Alignment:
    # Make the alignment of predict
    dest_time = datetime.strptime(t, REUTERS_DATETIME_FORMAT)
    dest_unixtime = dest_time.timestamp()

    ric_seqtype_to_keys = dict()
    ric_seqtype_to_unixtimes = dict()
    for (ric, seqtype) in itertools.product(rics, seqtypes):
        ric_seqtype_to_keys[(ric, seqtype)] = \
            [k for k in r.keys(ric + '__' + seqtype.value + '__*')]
        ric_seqtype_to_unixtimes[(ric, seqtype)] = \
            numpy.array([datetime.strptime(k.split('__')[2], REUTERS_DATETIME_FORMAT).timestamp()
                         for k in ric_seqtype_to_keys[(ric, seqtype)]], dtype=numpy.int64)

    # Find the latest prices for the selected time
    chart = dict()
    for (ric, seqtype) in itertools.product(rics, seqtypes):
        U = ric_seqtype_to_unixtimes[(ric, seqtype)]
        valid_indices = numpy.where(U <= dest_unixtime)
        if valid_indices[0].shape[0] == 0:
            vals = []
        else:
            i_max_sub = U[valid_indices].argmax()
            i_max = numpy.arange(U.shape[0])[valid_indices][i_max_sub]
            key = ric_seqtype_to_keys[(ric, seqtype)][i_max]
            vals = r.lrange(key, 0, -1)
        chart[stringify_ric_seqtype(ric, seqtype)] = vals

    processed_tokens = ['']
    article_id = 'dummy'

    return Alignment(article_id, t, dest_time.hour, processed_tokens, chart)


def create_dataset(config: Config,
                   device: torch.device,
                   rics: List[str],
                   seqtypes: List[SeqType]) -> Tuple[Vocab, Iterator]:
    # Make dataset
    fields = dict()
    fields[SeqType.ArticleID.value] = (SeqType.ArticleID.value, RawField())

    time_field = Field(use_vocab=False, batch_first=True, sequential=False)
    fields['jst_hour'] = (SeqType.Time.value, time_field)

    token_field = \
        Field(use_vocab=True,
              init_token=SpecialToken.BOS.value,
              eos_token=SpecialToken.EOS.value,
              pad_token=SpecialToken.Padding.value,
              unk_token=SpecialToken.Unknown.value)

    fields['processed_tokens'] = (SeqType.Token.value, token_field)

    tensor_type = torch.FloatTensor if device.type == 'cpu' else torch.cuda.FloatTensor

    for (ric, seqtype) in itertools.product(rics, seqtypes):
        n = N_LONG_TERM if seqtype.value.endswith('long') else N_SHORT_TERM
        price_field = Field(use_vocab=False,
                            fix_length=n,
                            batch_first=True,
                            pad_token=0.0,
                            preprocessing=lambda xs: [float(x) for x in xs],
                            tensor_type=tensor_type)
        key = stringify_ric_seqtype(ric, seqtype)
        fields[key] = (key, price_field)

    # read alignment of train and predict
    train = TabularDataset(path='output/alignment-train.json', format='json', fields=fields)
    predict = TabularDataset(path='output/alignment-predict.json', format='json', fields=fields)

    # build vocab from train tokens
    token_field.build_vocab(train, min_freq=config.token_min_freq)

    # make iteroter train and predict
    predict_iter = Iterator(predict,
                            batch_size=1,
                            device=-1 if device.type == 'cpu' else device,
                            repeat=False,
                            sort=False)

    return (token_field.vocab, predict_iter)


if __name__ == "__main__":
    predict()
