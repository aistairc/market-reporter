import csv
import math
import random
from itertools import permutations
from pathlib import Path
from typing import Dict

from sqlalchemy.orm.session import Session
from tqdm import tqdm

from reporter.database.model import HumanEvaluation, GenerationResult
from reporter.postprocessing.text import number2kansuuzi


def populate_for_human_evaluation(session: Session,
                                  method_to_result: Dict[str, Path]) -> None:

    if session.query(HumanEvaluation).first() is not None:
        return

    if session.query(GenerationResult).first() is not None:
        return

    method_names = list(method_to_result.keys()) + ['Gold']

    token_delim = '|'

    with method_to_result['Base'].open(mode='r') as f:
        N = sum(1 for _ in f) - 1
        f.seek(0)

        reader = csv.reader(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        next(reader)
        for _ in tqdm(range(N)):
            fields = next(reader)
            article_id = fields[0]
            base_result = GenerationResult(article_id,
                                           'Base',
                                           ''.join(number2kansuuzi(fields[4].split(token_delim)[:-1])))
            session.add(base_result)

            gold_result = GenerationResult(article_id, 'Gold', None)
            session.add(gold_result)

        session.commit()

    for method_name in [m for m in method_names if m not in ['Base', 'Gold']]:

        if not method_to_result[method_name].is_file():
            continue

        with method_to_result[method_name].open(mode='r') as f:
            N = sum(1 for _ in f) - 1
            f.seek(0)

            reader = csv.reader(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
            next(reader)
            for _ in tqdm(range(N)):
                fields = next(reader)
                article_id = fields[0]
                result = GenerationResult(article_id,
                                          method_name,
                                          ''.join(number2kansuuzi(fields[4].split(token_delim)[:-1])))
                session.add(result)
        session.commit()

    groups = session \
        .query(GenerationResult.article_id) \
        .filter(GenerationResult.result != '') \
        .group_by(GenerationResult.article_id) \
        .all()

    orderings = list(permutations([m for m in method_names]))

    for group in groups:

        i = random.randint(0, math.factorial(len(method_names)) - 1)
        h = HumanEvaluation(group.article_id, ordering=orderings[i])
        session.add(h)

    session.commit()

    results = session.query(HumanEvaluation).all()

    SAMPLE_SIZE = 100
    n_results = len(results)

    if n_results >= SAMPLE_SIZE:
        sample_indices = random.sample(range(n_results), SAMPLE_SIZE)

        for i, result in enumerate(results):
            result.is_target = i in sample_indices

        session.commit()
