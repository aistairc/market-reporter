import itertools
from logging import Logger
from pathlib import Path
from typing import Dict, List, Tuple

import boto3
import torch
from sqlalchemy.orm.session import Session
from torchtext.data import Field, Iterator, RawField, TabularDataset
from torchtext.vocab import Vocab

from reporter.database.read import Alignment, are_headlines_ready, fetch_rics
from reporter.database.write import (
    insert_headlines,
    insert_prices,
    update_headlines
)
from reporter.resource.reuters import download_prices_from_reuters
from reporter.resource.s3 import (
    download_nikkei_headlines_from_s3,
    download_prices_from_s3,
    list_rics_in_s3,
    upload_prices_to_s3
)
from reporter.util.config import Config
from reporter.util.constant import (
    N_LONG_TERM,
    N_SHORT_TERM,
    Phase,
    SeqType,
    SpecialToken
)
from reporter.util.conversion import stringify_ric_seqtype


def prepare_resources(config: Config, db_session: Session, logger: Logger) -> Dict[Phase, List[Alignment]]:

    existing_rics = fetch_rics(db_session)
    db_missing_rics = [ric for ric in config.rics if ric not in existing_rics]

    has_headlines = are_headlines_ready(db_session)

    dir_prices = Path(config.dir_resources, 'prices')
    boto3_session = \
        boto3.session.Session(aws_access_key_id=config.aws_access_key_id,
                              aws_secret_access_key=config.aws_secret_access_key,
                              region_name=config.aws_region) \
        if config.use_aws_env_variables \
        else boto3.session.Session(profile_name=config.aws_profile_name)

    bucket_name = config.s3_bucket_name
    s3 = boto3_session.resource('s3')
    s3.meta.client.head_bucket(Bucket=bucket_name)
    bucket = s3.Bucket(bucket_name)

    dir_cp932_headlines = Path(config.dir_resources, 'headlines', 'cp932zip')
    dir_headlines = Path(config.dir_resources, 'headlines', 'utf8csv')

    if not has_headlines:
        download_nikkei_headlines_from_s3(bucket,
                                          dir_cp932_headlines,
                                          dir_headlines,
                                          config.remote_nikkei_headline_filenames,
                                          logger)

    remote_rics = list_rics_in_s3(bucket, config.remote_dir_prices)
    remote_missing_rics = [ric for ric in config.rics if ric not in remote_rics]
    remote_dir_prices = Path(config.remote_dir_prices)
    if len(remote_missing_rics) > 0:
        download_prices_from_reuters(config.reuters_username,
                                     config.reuters_password,
                                     dir_prices,
                                     remote_missing_rics,
                                     logger)
        upload_prices_to_s3(bucket, dir_prices, remote_dir_prices, remote_missing_rics)

    download_prices_from_s3(bucket, dir_prices, remote_dir_prices, db_missing_rics, logger)

    insert_prices(db_session, dir_prices, db_missing_rics, config.dir_resources, logger)

    insert_headlines(db_session,
                     dir_headlines,
                     train_span=config.train_span,
                     valid_span=config.valid_span,
                     test_span=config.test_span,
                     logger=logger)

    update_headlines(db_session, config.dir_resources / Path('user-dict.csv'), logger)


def create_dataset(config: Config, device: torch.device) -> Tuple[Vocab, Iterator, Iterator, Iterator]:

    fields = dict()
    raw_field = RawField()
    # torchtext 0.3.1
    # AttributeError: 'RawField' object has no attribute 'is_target'
    raw_field.is_target = False
    fields[SeqType.ArticleID.value] = (SeqType.ArticleID.value, raw_field)

    time_field = Field(use_vocab=False, batch_first=True, sequential=False)
    fields['jst_hour'] = (SeqType.Time.value, time_field)

    token_field = \
        Field(use_vocab=True,
              init_token=SpecialToken.BOS.value,
              eos_token=SpecialToken.EOS.value,
              pad_token=SpecialToken.Padding.value,
              unk_token=SpecialToken.Unknown.value) \
        if config.use_init_token_tag \
        else Field(use_vocab=True,
                   eos_token=SpecialToken.EOS.value,
                   pad_token=SpecialToken.Padding.value,
                   unk_token=SpecialToken.Unknown.value)

    fields['processed_tokens'] = (SeqType.Token.value, token_field)

    seqtypes = [SeqType.RawShort, SeqType.RawLong,
                SeqType.MovRefShort, SeqType.MovRefLong,
                SeqType.NormMovRefShort, SeqType.NormMovRefLong,
                SeqType.StdShort, SeqType.StdLong]

    for (ric, seqtype) in itertools.product(config.rics, seqtypes):
        n = N_LONG_TERM \
            if seqtype.value.endswith('long') \
            else N_SHORT_TERM
        price_field = Field(use_vocab=False,
                            fix_length=n,
                            batch_first=True,
                            pad_token=0.0,
                            preprocessing=lambda xs: [float(x) for x in xs],
                            dtype=torch.float)
        key = stringify_ric_seqtype(ric, seqtype)
        fields[key] = (key, price_field)

    train, val, test = \
        TabularDataset.splits(path=str(config.dir_output),
                              format='json',
                              train='alignment-train.json',
                              validation='alignment-valid.json',
                              test='alignment-test.json',
                              fields=fields)

    token_field.build_vocab(train, min_freq=config.token_min_freq)

    batch_size = config.batch_size
    train_iter, val_iter, test_iter = \
        Iterator.splits((train, val, test),
                        batch_sizes=(batch_size, batch_size, batch_size),
                        device=-1 if device.type == 'cpu' else device,
                        repeat=False,
                        sort=False)

    return (token_field.vocab, train_iter, val_iter, test_iter)
