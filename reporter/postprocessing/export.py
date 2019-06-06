import csv
from pathlib import Path

from reporter.core.train import RunResult


def export_results_to_csv(dest_dir: Path, result: RunResult) -> None:

    header = ['article_id',
              'gold tokens (tag)',
              'gold tokens (num)',
              'pred tokens (tag)',
              'pred tokens (num)']
    dest_dir.mkdir(parents=True, exist_ok=True)
    output_file = dest_dir / Path('reporter.csv')

    with output_file.open(mode='w') as w:
        writer = csv.writer(w, delimiter=',', quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        for (article_id, gold_sent, gold_sent_num, pred_sent, pred_sent_num) in \
                zip(result.article_ids,
                    result.gold_sents,
                    result.gold_sents_num,
                    result.pred_sents,
                    result.pred_sents_num):
            writer.writerow([article_id,
                             '|'.join(gold_sent),
                             '|'.join(gold_sent_num),
                             '|'.join(pred_sent),
                             '|'.join(pred_sent_num)])
