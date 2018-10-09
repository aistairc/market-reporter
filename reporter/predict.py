import argparse
import errno
import itertools
import os
from datetime import datetime
from pathlib import Path
from typing import List

import jsonlines
import redis
import torch
from redis import Redis
from torchtext.data import Field, Iterator, RawField, TabularDataset
from torchtext.vocab import Vocab
from sqlalchemy import func
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import Session, sessionmaker

from reporter.core.network import Decoder, Encoder, EncoderDecoder, setup_attention
from reporter.core.operation import get_latest_closing_vals, replace_tags_with_vals
from reporter.database.read import Alignment, fetch_latest_vals
from reporter.database.model import Price, Close
from reporter.postprocessing.text import remove_bos
from reporter.util.config import Config
from reporter.util.constant import (
    N_LONG_TERM,
    N_SHORT_TERM,
    NIKKEI_DATETIME_FORMAT,
    REUTERS_DATETIME_FORMAT,
    Code,
    Phase,
    SeqType,
    SpecialToken)
from reporter.util.conversion import stringify_ric_seqtype
from reporter.util.tool import takeuntil


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
    parser.add_argument('-o',
                        '--output',
                        type=str,
                        metavar='DIRECTORYNAME',
                        help='specify directory of the model file and the vocab file')
    parser.add_argument('-t',
                        '--time',
                        type=str,
                        help='Datetime (format: `year-month-day hour:minute:second+timezone`)')
    parser.add_argument('-r',
                        '--ric',
                        type=str,
                        help='Reuters Insturument Code (e.g. `.N225`: Nikkei Stock Average)')

    return parser.parse_args()


class Predictor:

    def __init__(self, config: Config, device: torch.device, output: Path):

        self.config = config

        self.device = device

        dest_pretrained_model = output / Path('reporter.model')

        dest_train_vocab = output / Path('reporter.vocab')

        if not dest_pretrained_model.is_file():
            raise FileNotFoundError(errno.ENOENT,
                                    os.strerror(errno.ENOENT),
                                    str(dest_pretrained_model))

        if not dest_train_vocab.is_file():
            raise FileNotFoundError(errno.ENOENT,
                                    os.strerror(errno.ENOENT),
                                    str(dest_train_vocab))

        self.seqtypes = [SeqType.RawShort, SeqType.RawLong,
                         SeqType.MovRefShort, SeqType.MovRefLong,
                         SeqType.NormMovRefShort, SeqType.NormMovRefLong,
                         SeqType.StdShort, SeqType.StdLong]

        self.vocab = None
        with dest_train_vocab.open('rb') as f:
            self.vocab = torch.load(f)

        vocab_size = len(self.vocab)
        attn = setup_attention(self.config, self.seqtypes)
        encoder = Encoder(self.config, self.device)
        decoder = Decoder(self.config, vocab_size, attn, self.device)
        self.model = EncoderDecoder(encoder, decoder, self.device)
        self.criterion = \
            torch.nn.NLLLoss(reduction='elementwise_mean',
                             ignore_index=self.vocab.stoi[SpecialToken.Padding.value])

        with dest_pretrained_model.open(mode='rb') as f:
            self.model.load_state_dict(torch.load(f))

    def predict(self, t: str, target_ric: str) -> List[str]:
        # Connect to Postgres
        engine = create_engine(self.config.db_uri)
        SessionMaker = sessionmaker(bind=engine)
        pg_session = SessionMaker()

        # Connect to Redis

        rics = self.config.rics \
            if target_ric in self.config.rics \
            else [target_ric] + self.config.rics

        alignments = load_alignments_from_db(pg_session, rics, t, self.seqtypes)

        # Write the prediction data
        self.config.dir_output.mkdir(parents=True, exist_ok=True)
        dest_alignments = self.config.dir_output / Path('alignment-predict.json')
        with dest_alignments.open(mode='w') as f:
            writer = jsonlines.Writer(f)
            writer.write(alignments.to_dict())

        predict_iter = create_dataset(self.config,
                                      self.device,
                                      self.vocab,
                                      rics,
                                      self.seqtypes)

        self.model.eval()

        batch = next(iter(predict_iter))

        times = batch.time
        tokens = batch.token
        raw_short_field = stringify_ric_seqtype(Code.N225.value, SeqType.RawShort)
        latest_vals = [x for x in getattr(batch, raw_short_field).data[:, 0]]
        raw_long_field = stringify_ric_seqtype(Code.N225.value, SeqType.RawLong)
        latest_closing_vals = get_latest_closing_vals(batch, raw_long_field, times)

        loss, pred, attn_weight = self.model(batch,
                                             batch.batch_size,
                                             tokens,
                                             times,
                                             self.criterion,
                                             Phase.Test)

        i_eos = self.vocab.stoi[SpecialToken.EOS.value]
        pred_sents = [remove_bos([self.vocab.itos[i] for i in takeuntil(i_eos, sent)])
                      for sent in zip(*pred)]

        return replace_tags_with_vals(pred_sents[0], latest_closing_vals[0], latest_vals[0])


def load_alignments_from_db(session: Session,
                            rics: List[str],
                            t: str,
                            seqtypes: List[SeqType]) -> Alignment:
    time = datetime.strptime(t, NIKKEI_DATETIME_FORMAT)
    chart = dict([fetch_latest_vals(session, time, ric, seqtype)
                  for (ric, seqtype) in itertools.product(rics, seqtypes)])
    processed_tokens = ['']
    article_id = 'dummy'
    return Alignment(article_id, t, time.hour, processed_tokens, chart)


def create_dataset(config: Config,
                   device: torch.device,
                   vocab: Vocab,
                   rics: List[str],
                   seqtypes: List[SeqType]) -> Iterator:

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

    # load an alignment for predicttion
    predict = TabularDataset(path='output/alignment-predict.json',
                             format='json',
                             fields=fields)

    token_field.vocab = vocab

    # Make an iteroter for prediction
    return Iterator(predict,
                    batch_size=1,
                    device=-1 if device.type == 'cpu' else device,
                    repeat=False,
                    sort=False)


def main() -> None:

    args = parse_args()

    predictor = Predictor(Config(args.dest_config),
                          torch.device(args.device),
                          Path(args.output))

    sentence = predictor.predict(args.time, args.ric)

    print('"' + '", "'.join(sentence) + '"')


if __name__ == "__main__":
    main()
