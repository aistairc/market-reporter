import argparse
import json
import warnings
from datetime import datetime
from pathlib import Path
from functools import reduce

import jsonlines
import torch

from reporter.core.network import Decoder, Encoder, EncoderDecoder, setup_attention
from reporter.core.train import run
from reporter.database.model import create_tables
from reporter.database.read import load_alignments_from_db
from reporter.postprocessing.bleu import calc_bleu
from reporter.preprocessing.dataset import create_dataset, prepare_resources
from reporter.util.config import Config
from reporter.util.constant import Phase, SpecialToken
from reporter.util.logging import create_logger


def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(prog='reporter')
    parser.add_argument('--device',
                        type=str,
                        metavar='DEVICE',
                        default='cpu',
                        help='`cuda:n` where `n` is an integer, or `cpu`')
    parser.add_argument('--debug',
                        dest='is_debug',
                        action='store_true',
                        default=False,
                        help='show detailed messages while execution')
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
    return parser.parse_args()


def main() -> None:

    args = parse_args()

    if not args.is_debug:
        warnings.simplefilter(action='ignore', category=FutureWarning)

    config = Config(args.dest_config)

    device = torch.device(args.device)

    now = datetime.today().strftime('reporter-%Y-%m-%d-%H-%M-%S')
    dest_log = config.dir_output / Path(now) / Path('reporter.log')

    logger = create_logger(dest_log,  is_debug=args.is_debug)
    config.write_log(logger)

    message = 'start main (is_debug: {}, device: {})'.format(args.is_debug, args.device)
    logger.info(message)

    if not config.dest_dataset.is_file():

        # === Alignment ===
        has_all_alignments = \
            reduce(lambda x, y: x and y,
                   [(config.dir_output / Path('alignment-{}.json'.format(phase.value))).exists()
                    for phase in list(Phase)])
        if not has_all_alignments:

            from sqlalchemy.engine import create_engine
            from sqlalchemy.orm.session import sessionmaker
            engine = create_engine(config.db_uri)
            SessionMaker = sessionmaker(bind=engine)
            pg_session = SessionMaker()
            create_tables(engine)

            import redis
            from redis.exceptions import ConnectionError
            redis_db_index = config.redis['db']
            if not isinstance(redis_db_index, int) or redis_db_index < 0:
                raise ConnectionError('DB index is {}. Please specify a zero-based numeric index.'
                                      .format(redis_db_index))

            connection_pool = redis.ConnectionPool(**config.redis)
            redis_client = redis.StrictRedis(connection_pool=connection_pool)

            prepare_resources(config, pg_session, redis_client, logger)
            for phase in list(Phase):
                config.dir_output.mkdir(parents=True, exist_ok=True)
                dest_alignments = config.dir_output / Path('alignment-{}.json'.format(phase.value))
                alignments = load_alignments_from_db(pg_session, redis_client, phase, logger)
                with dest_alignments.open(mode='w') as f:
                    writer = jsonlines.Writer(f)
                    writer.write_all(alignments)
            pg_session.close()

        # === Dataset ===
        (vocab, train, valid, test) = create_dataset(config, device)

        vocab_size = len(vocab)
        dest_vocab = config.dir_output / Path(now) / Path('reporter.vocab')
        with dest_vocab.open(mode='wb') as f:
            torch.save(vocab, f)
        seqtypes = []
        attn = setup_attention(config, seqtypes)
        encoder = Encoder(config, device)
        decoder = Decoder(config, vocab_size, attn, device)
        model = EncoderDecoder(encoder, decoder, device)
        optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
        criterion = torch.nn.NLLLoss(reduction='elementwise_mean',
                                     ignore_index=vocab.stoi[SpecialToken.Padding.value])

    # === Train ===
    dest_model = config.dir_output / Path(now) / Path('reporter.model')
    prev_valid_bleu = 0.0
    max_bleu = 0.0
    best_epoch = 0
    early_stop_counter = 0
    for epoch in range(config.n_epochs):
        logger.info('start epoch {}'.format(epoch))
        train_result = run(train,
                           vocab,
                           model,
                           optimizer,
                           criterion,
                           Phase.Train,
                           logger)
        train_bleu = calc_bleu(train_result.gold_sents, train_result.pred_sents)
        valid_result = run(valid,
                           vocab,
                           model,
                           optimizer,
                           criterion,
                           Phase.Valid,
                           logger)
        valid_bleu = calc_bleu(valid_result.gold_sents, valid_result.pred_sents)

        s = ' | '.join(['epoch: {0:4d}'.format(epoch),
                        'training loss: {:.2f}'.format(train_result.loss),
                        'training BLEU: {:.4f}'.format(train_bleu),
                        'validation loss: {:.2f}'.format(valid_result.loss),
                        'validation BLEU: {:.4f}'.format(valid_bleu)])
        logger.info(s)

        if max_bleu < valid_bleu:
            torch.save(model.state_dict(), str(dest_model))
            max_bleu = valid_bleu
            best_epoch = epoch

        early_stop_counter += int(prev_valid_bleu > valid_bleu)
        if early_stop_counter == config.patience:
            logger.info('EARLY STOPPING')
            break
        prev_valid_bleu = valid_bleu

    # === Test ===
    with dest_model.open(mode='rb') as f:
        model.load_state_dict(torch.load(f))
    test_result = run(test,
                      vocab,
                      model,
                      optimizer,
                      criterion,
                      Phase.Test,
                      logger)
    test_bleu = calc_bleu(test_result.gold_sents, test_result.pred_sents)

    s = ' | '.join(['epoch: {:04d}'.format(best_epoch),
                    'Test Loss: {:.2f}'.format(test_result.loss),
                    'Test BLEU: {:.10f}'.format(test_bleu)])
    logger.info(s)


if __name__ == '__main__':
    main()
