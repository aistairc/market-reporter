from sqlalchemy import not_
from sqlalchemy.orm import Query

from reporter.database.model import Headline, HumanEvaluation


def construct_constraint_query(field: str, relation: str, condition: str) -> Query:

    table = Headline if field in ['article_id', 't', 'phase', 'headline'] else HumanEvaluation

    if relation == '=':
        return getattr(table, field) == condition
    elif relation == '!=':
        return getattr(table, field) != condition
    elif relation in ['&gt;', '>']:
        return getattr(table, field) > condition
    elif relation in ['&gt;=', '>=']:
        return getattr(table, field) >= condition
    elif relation in ['&lt;', '<']:
        return getattr(table, field) < condition
    elif relation in ['&lt;=', '<=']:
        return getattr(table, field) <= condition
    elif relation == 'like':
        return getattr(table, field).like(condition)
    elif relation == 'not like':
        return not_(getattr(table, field).like(condition))
    elif relation == 'is null':
        return getattr(table, field).is_(None)
    elif relation == 'is not null':
        return getattr(table, field).isnot(None)
    else:
        return True
