import csv

from pathlib import Path

from reporter.core.train import RunResult


def export_results_to_csv(dest_dir: Path,
                          results: RunResult) -> None:

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
        for article_id, tag_gold, num_gold, tag_pred, num_pred in \
            zip(results.article_ids,
                results.gold_sents,
                results.gold_sents_num,
                results.pred_sents,
                results.pred_sents_num):
            writer.writerow([article_id,
                             '|'.join(tag_gold),
                             '|'.join(num_gold),
                             '|'.join(tag_pred),
                             '|'.join(num_pred)])
