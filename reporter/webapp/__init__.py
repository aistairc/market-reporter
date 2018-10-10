from datetime import datetime, timedelta, timezone
from typing import List

import http
import flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

from reporter.database.misc import in_jst, in_utc
from reporter.database.model import Headline, HumanEvaluation, GenerationResult
from reporter.database.read import fetch_max_t_of_prev_trading_day, fetch_rics, fetch_date_range
from reporter.util.config import Config
from reporter.util.constant import UTC, Code, NIKKEI_DATETIME_FORMAT
from reporter.webapp.human_evaluation import populate_for_human_evaluation
from reporter.webapp.table import load_ric_to_ric_info, create_ric_tables, Table
from reporter.webapp.search import construct_constraint_query
from reporter.webapp.chart import fetch_points
from reporter.predict import Predictor

import os
import torch
from pathlib import Path


config = Config('config.toml')
app = flask.Flask(__name__)
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = config.db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.jinja_env.add_extension('pypugjs.ext.jinja.PyPugJSExtension')
db = SQLAlchemy(app)

ric_to_ric_info = load_ric_to_ric_info()
populate_for_human_evaluation(db.session, config.result)

device = os.environ.get('DEVICE', 'cpu')
output = os.environ.get('OUTPUT', 'output')

predictor = Predictor(config,
                      torch.device(device),
                      Path(output))


class EvalTarget:
    def __init__(self, method_name: str, text: str, is_debug: bool):
        self.method_name = method_name
        self.text = text
        self.is_debug = is_debug


class EvalListRow:
    def __init__(self,
                 article_id: str,
                 jst: str,
                 phase: str,
                 eval_targets: List[EvalTarget],
                 fluency: str,
                 informativeness: str,
                 note: str,
                 is_target: bool,
                 is_finished: bool):
        self.article_id = article_id
        self.jst = jst
        self.phase = phase
        self.methods = eval_targets
        self.fluency = fluency
        self.informativeness = informativeness
        self.note = note
        self.is_target = is_target
        self.is_finished = is_finished


class DummyPagination:
    def __init__(self, has_prev: bool, has_next: bool, display_msg: str):
        self.has_prev = has_prev
        self.has_next = has_next
        self.display_msg = display_msg


def order_method_names_for_debug(method_names: List[str]) -> List[str]:
    result = []
    if 'Gold' in method_names:
        result.append((0, 'Gold'))

    if 'Base' in method_names:
        result.append((1, 'Base'))

    for method_name in [m for m in method_names if m not in ['Gold', 'Base']]:
        result.append((2, method_name))

    return [m for (_, m) in sorted(result)]


@app.route('/')
def index() -> flask.Response:
    return flask.redirect('/debug', code=http.HTTPStatus.FOUND)


def list_targets_of_human_evaluation(is_debug: bool) -> flask.Response:
    args = flask.request.args
    page = int(args.get('page', default=1))
    conditions = []
    for i in range(5):
        field = args.get('field' + str(i))
        relation = args.get('rel' + str(i))
        val = args.get('val' + str(i))
        if field is not None and relation is not None and val is not None:
            constraint = construct_constraint_query(field.strip(), relation.strip(), val.strip())
            conditions.append(constraint)

    q = db \
        .session \
        .query(HumanEvaluation.article_id,
               HumanEvaluation.ordering,
               HumanEvaluation.is_target,
               (func.coalesce(HumanEvaluation.fluency, '')).label('fluency'),
               (func.coalesce(HumanEvaluation.informativeness, '')).label('informativeness'),
               (func.coalesce(HumanEvaluation.note, '')).label('note'),
               Headline.simple_headline.label('gold_result'),
               Headline.phase,
               func.to_char(in_jst(Headline.t), 'YYYY-MM-DD HH24:MI').label('jst')) \
        .outerjoin(Headline,
                   HumanEvaluation.article_id == Headline.article_id) \
        .filter(Headline.is_used.is_(True), *conditions) \
        .order_by(Headline.t)

    n_results = q.count()
    per_page = config.n_items_per_page
    articles = []
    for h in q.limit(per_page).offset((page - 1) * per_page).all():
        method_names = ['Gold'] if h.ordering is None else h.ordering
        if is_debug:
            method_names = order_method_names_for_debug(method_names)

        eval_targets = []
        for method_name in method_names:
            res = db \
                .session \
                .query(GenerationResult.article_id,
                       GenerationResult.result,
                       GenerationResult.correctness) \
                .filter(GenerationResult.article_id == h.article_id,
                        GenerationResult.method_name == method_name) \
                .one_or_none()

            if res is None:
                et = EvalTarget(method_name, h.gold_result, None) \
                     if method_name == 'Gold' \
                     else EvalTarget(method_name, '', None)
            else:
                text = h.gold_result \
                    if method_name == 'Gold' \
                    else res.result
                et = EvalTarget(method_name, text, is_debug)
                eval_targets.append(et)

        is_finished = \
            len(list(config.result.keys()) + ['Gold']) == \
            len(h.fluency) > 0 \
            and len(h.informativeness) > 0

        e = EvalListRow(h.article_id,
                        h.jst,
                        h.phase,
                        eval_targets,
                        h.fluency,
                        h.informativeness,
                        h.note,
                        h.is_target,
                        is_finished)
        articles.append(e)

    if n_results == 0:
        display_msg = 'No headline is found'
    else:
        offset = (page - 1) * per_page + 1
        end = offset + per_page - 1 if page < (n_results // per_page) else n_results
        display_msg = 'Displaying {:,} to {:,} of {:,}'.format(offset, end, n_results)

    pagination = DummyPagination(has_prev=page > 1,
                                 has_next=page < (n_results // per_page),
                                 display_msg=display_msg)

    return flask.render_template('list_human_evaluation.pug',
                                 title='debug' if is_debug else 'human-evaluation',
                                 condition=conditions,
                                 articles=articles,
                                 pagination=pagination)


def article_evaluation(article_id: str,
                       method: str,
                       is_debug: bool) -> flask.Response:

    if method == 'POST':

        h = db \
            .session \
            .query(HumanEvaluation) \
            .filter(HumanEvaluation.article_id == article_id) \
            .one()

        form = flask.request.form
        nth = dict([(method_name, i + 1) for (i, method_name) in enumerate(h.ordering)])

        note = form.get('note')
        h.note = None \
            if note is None or note.strip() == '' \
            else note

        fluency = form.get('fluency')
        h.fluency = None \
            if fluency is None or fluency.strip() == '' \
            else fluency

        informativeness = form.get('informativeness')
        h.informativeness = None \
            if informativeness is None or informativeness.strip() == '' \
            else informativeness

        r = db \
            .session \
            .query(GenerationResult) \
            .filter(GenerationResult.article_id == article_id,
                    GenerationResult.method_name == 'Base') \
            .one()
        r.correctness = form.get('correctness-{}'.format(nth['Base']))

        g = db \
            .session \
            .query(GenerationResult) \
            .filter(GenerationResult.article_id == article_id,
                    GenerationResult.method_name == 'Gold') \
            .one()
        g.correctness = form.get('correctness-{}'.format(nth['Gold']))

        e = db \
            .session \
            .query(GenerationResult) \
            .filter(GenerationResult.article_id == article_id,
                    GenerationResult.method_name == 'Extr') \
            .one()
        e.correctness = form.get('correctness-{}'.format(nth['Extr']))

        db.session.commit()

        referrer = flask.request.form.get('referrer', '/')
        return flask.redirect(referrer)
    else:
        headline = db \
            .session \
            .query(Headline.article_id,
                   Headline.simple_headline.label('gold_result'),
                   Headline.t,
                   func.to_char(in_jst(Headline.t), 'YYYY-MM-DD HH24:MI:SS').label('s_jst')) \
            .filter(Headline.article_id == article_id) \
            .one()

        ric_tables = create_ric_tables(db.session, config.rics, ric_to_ric_info, headline.t)
        group_size = 3
        while len(ric_tables) % 3 != 0:
            ric_tables.append(Table('', '', '', [], is_dummy=True))
        ric_table_groups = [ric_tables[i:i + group_size]
                            for i in range(0, len(ric_tables), group_size)]
        # It is better to share one procedure with the search,
        # but we keep this procedure for convenience
        target = db \
            .session \
            .query(HumanEvaluation) \
            .filter(HumanEvaluation.article_id == article_id) \
            .one_or_none()

        targets = []
        method_names = ['Gold'] if target.ordering is None else target.ordering
        if is_debug:
            method_names = order_method_names_for_debug(method_names)
        d = dict()
        m = []
        for method_name in method_names:
            res = db \
                  .session \
                  .query(GenerationResult.article_id,
                         GenerationResult.result,
                         GenerationResult.correctness) \
                  .filter(GenerationResult.article_id == article_id,
                          GenerationResult.method_name == method_name) \
                  .one_or_none()

            if res is not None:
                text = headline.gold_result \
                    if method_name == 'Gold' \
                    else res.result
                d[method_name] = EvalTarget(method_name, text, is_debug)
                m.append(method_name)

        note = '' if target.note is None else target.note
        fluency = '' if target.fluency is None else target.fluency
        informativeness = '' if target.informativeness is None else target.informativeness
        targets = [(i + 1, d[method_name]) for (i, method_name) in enumerate(m)]

        return flask.render_template('human_evaluation.pug',
                                     title='debug' if is_debug else 'human-evaluation',
                                     article_id=headline.article_id,
                                     timestamp=headline.s_jst + ' JST',
                                     targets=targets,
                                     fluency=fluency,
                                     informativeness=informativeness,
                                     note=note,
                                     ric_table_groups=ric_table_groups)


@app.route('/data/<string:article_id>')
def data(article_id: str) -> flask.Response:

    headline = db \
        .session \
        .query(Headline, in_utc(Headline.t).label('utc')) \
        .filter(Headline.article_id == article_id) \
        .one()

    data = []
    for ric in [Code.N225.value, Code.TOPIX.value]:

        end = headline.utc.replace(tzinfo=UTC)
        start = datetime(end.year, end.month, end.day, 0, 0, tzinfo=UTC)
        xs, ys = fetch_points(db.session, ric, start, end)

        end_prev = datetime \
            .utcfromtimestamp(fetch_max_t_of_prev_trading_day(db.session, ric, end)) \
            .replace(tzinfo=UTC)
        start_prev = datetime(end_prev.year, end_prev.month, end_prev.day, 0, 0, tzinfo=UTC)
        xs_prev, ys_prev = fetch_points(db.session, ric, start_prev, end_prev)

        data.append({
            'ric': ric,
            'chart': {
                'xs': xs,
                'ys': ys,
                'title': '{} {}'.format(ric, end.strftime('%Y-%m-%d'))
            },
            'chart-prev': {
                'xs': xs_prev,
                'ys': ys_prev,
                'title': '{} {}'.format(ric, end_prev.strftime('%Y-%m-%d'))
            }
        })

    return app.response_class(response=flask.json.dumps(data),
                              status=http.HTTPStatus.OK,
                              mimetype='application/json')


@app.route('/human-evaluation')
def human_evaluation() -> flask.Response:
    return flask.redirect('/human-evaluation/list', code=http.HTTPStatus.FOUND)


@app.route('/debug')
def debug() -> flask.Response:
    return flask.redirect('/debug/list', code=http.HTTPStatus.FOUND)


@app.route('/<string:page_name>/list')
def list_targets(page_name: str) -> flask.Response:
    return list_targets_of_human_evaluation(is_debug=page_name == 'debug')


@app.route('/<string:page_name>/article/<string:article_id>', methods=['POST', 'GET'])
def articles(page_name: str, article_id: str) -> flask.Response:
    return article_evaluation(article_id,
                              flask.request.method,
                              is_debug=page_name == 'debug')

@app.route('/demo')
def demo() -> flask.Response:
    min_date, max_date = fetch_date_range(db.session)
    rics = fetch_rics(db.session)
    return flask.render_template('demo.pug', title='demo',
        min_date=min_date.timestamp(),
        max_date=max_date.timestamp(),
        rics=rics,
        rics_json=flask.json.dumps(rics)
    )

@app.route('/data_ts/<string:timestamp>')
def data_ts(timestamp: str) -> flask.Response:
    start = datetime.fromtimestamp(int(timestamp), timezone.utc)
    end = start + timedelta(days=1)

    rics = fetch_rics(db.session)
    data = {
        'start': start.timestamp(),
        'end': end.timestamp(),
        'data': {}
    }

    for ric in rics:
        xs, ys = fetch_points(db.session, ric, start, end)

        data['data'][ric] = {
            'xs': xs,
            'ys': ys,
            'title': '{} {}'.format(ric, start.strftime('%Y-%m-%d'))
        }

    return app.response_class(response=flask.json.dumps(data),
                              status=http.HTTPStatus.OK,
                              mimetype='application/json')

@app.route('/predict/<string:ric>/<string:timestamp>')
def predict(ric: str, timestamp: str) -> flask.Response:
    time = datetime.fromtimestamp(int(timestamp), timezone.utc)
    sentence = predictor.predict(time.strftime(NIKKEI_DATETIME_FORMAT), ric)
    return app.response_class(response=flask.json.dumps(sentence),
                              status=http.HTTPStatus.OK,
                              mimetype='application/json')
