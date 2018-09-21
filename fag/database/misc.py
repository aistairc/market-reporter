from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.functions import Function


def in_jst(timestamp: datetime) -> Function:
    return func.timezone('Asia/Tokyo', timestamp)


def in_utc(timestamp: datetime) -> Function:
    return func.timezone('UTC', timestamp)


def stringify(query: Any) -> str:

    if type(query) == Query:
        query = query.statement
    else:
        pass

    sql = query.compile(compile_kwargs={"literal_binds": True},
                        dialect=postgresql.dialect())

    return str(sql)
