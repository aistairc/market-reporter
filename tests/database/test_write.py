from pathlib import Path

import pytest
from numpy import allclose
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker

from reporter.database.model import Base, Close, Instrument, Price, PriceSeq
from reporter.database.write import insert_prices
from reporter.util.config import Config
from reporter.util.constant import SeqType
from reporter.util.logging import create_logger


@pytest.fixture(scope='session')
def config():
    return Config('config.toml')


@pytest.fixture(scope='session')
def engine(config):
    return create_engine(config.db_uri)


@pytest.fixture(scope='session')
def db_session(config, engine):
    tables = [
        Close.__table__,
        Instrument.__table__,
        Price.__table__,
        PriceSeq.__table__]
    Base.metadata.drop_all(engine, tables)
    Base.metadata.create_all(engine, tables)

    Session = sessionmaker(bind=engine)

    session = Session()
    dir_resources = Path(config.dir_resources)
    dir_prices = dir_resources / Path('pseudo-data') / Path('prices')
    missing_rics = ['.TEST']
    logger = create_logger(Path('test.log'), is_debug=False, is_temporary=True)

    insert_prices(session, dir_prices, missing_rics, dir_resources, logger)

    yield session


def test_raw_long(db_session) -> None:
    expected = [140600.0, 130600.0, 120600.0, 110600.0, 70600.0, 60600.0, 50600.0]
    result = db_session \
        .query(PriceSeq.vals) \
        .filter(PriceSeq.ric == '.TEST',
                PriceSeq.t == '2011-01-14T06:00:00+0000',
                PriceSeq.seqtype == SeqType.RawLong.value) \
        .scalar()
    assert allclose(expected, result)


def test_standardized_long(db_session) -> None:
    expected = [1.367748, 1.095890, 0.824032, 0.552174, -0.535256, -0.807114, -1.078972]
    result = db_session \
        .query(PriceSeq.vals) \
        .filter(PriceSeq.ric == '.TEST',
                PriceSeq.t == '2011-01-14T06:00:00+0000',
                PriceSeq.seqtype == SeqType.StdLong.value) \
        .scalar()
    assert allclose(expected, result)


def test_moving_reference_long(db_session) -> None:
    expected = [10000.0, 10000.0, 10000.0, 40000.0, 10000.0, 10000.0]
    result = db_session \
        .query(PriceSeq.vals) \
        .filter(PriceSeq.ric == '.TEST',
                PriceSeq.t == '2011-01-14T06:00:00+0000',
                PriceSeq.seqtype == SeqType.MovRefLong.value) \
        .scalar()
    assert allclose(expected, result)


def test_normalized_moving_reference_long(db_session) -> None:
    expected = [-1.0, -1.0, -1.0, 1.0, -1.0, -1.0]
    result = db_session \
        .query(PriceSeq.vals) \
        .filter(PriceSeq.ric == '.TEST',
                PriceSeq.t == '2011-01-14T06:00:00+0000',
                PriceSeq.seqtype == SeqType.NormMovRefLong.value) \
        .scalar()
    assert allclose(expected, result)


def test_raw_short(db_session) -> None:
    expected = [140600.0, 140555.0, 140550.0, 140545.0, 140540.0,
                140535.0, 140530.0, 140525.0, 140520.0, 140515.0,
                140510.0, 140505.0, 140500.0, 140455.0, 140450.0,
                140445.0, 140440.0, 140435.0, 140430.0, 140425.0,
                140420.0, 140415.0, 140410.0, 140405.0, 140400.0,
                140355.0, 140350.0, 140345.0, 140340.0, 140335.0,
                140330.0, 140200.0, 140155.0, 140150.0, 140145.0,
                140140.0, 140135.0, 140130.0, 140125.0, 140120.0,
                140115.0, 140110.0, 140105.0, 140100.0, 140055.0,
                140050.0, 140045.0, 140040.0, 140035.0, 140030.0,
                140025.0, 140020.0, 140015.0, 140010.0, 140005.0,
                140000.0, 130600.0, 130555.0, 130550.0, 130545.0,
                130540.0, 130535.0]
    result = db_session \
        .query(PriceSeq.vals) \
        .filter(PriceSeq.ric == '.TEST',
                PriceSeq.t == '2011-01-14T06:00:00+0000',
                PriceSeq.seqtype == SeqType.RawShort.value) \
        .scalar()
    assert allclose(expected, result)


def test_standardized_short(db_session) -> None:
    expected = [1.367748, 1.366524, 1.366388, 1.366252, 1.366116,
                1.365980, 1.365845, 1.365709, 1.365573, 1.365437,
                1.365301, 1.365165, 1.365029, 1.363806, 1.363670,
                1.363534, 1.363398, 1.363262, 1.363126, 1.362990,
                1.362854, 1.362718, 1.362582, 1.362446, 1.362310,
                1.361087, 1.360951, 1.360815, 1.360679, 1.360543,
                1.360407, 1.356873, 1.355650, 1.355514, 1.355378,
                1.355242, 1.355106, 1.354970, 1.354834, 1.354698,
                1.354562, 1.354426, 1.354291, 1.354155, 1.352931,
                1.352795, 1.352659, 1.352523, 1.352388, 1.352252,
                1.352116, 1.351980, 1.351844, 1.351708, 1.351572,
                1.351436, 1.095890, 1.094666, 1.094531, 1.094395,
                1.094259, 1.094123]
    result = db_session \
        .query(PriceSeq.vals) \
        .filter(PriceSeq.ric == '.TEST',
                PriceSeq.t == '2011-01-14T06:00:00+0000',
                PriceSeq.seqtype == SeqType.StdShort.value) \
        .scalar()
    assert allclose(expected, result)


def test_moving_reference_short(db_session) -> None:
    expected = [10000.0, 9955.0, 9950.0, 9945.0, 9940.0,
                9935.0, 9930.0, 9925.0, 9920.0, 9915.0,
                9910.0, 9905.0, 9900.0, 9855.0, 9850.0,
                9845.0, 9840.0, 9835.0, 9830.0, 9825.0,
                9820.0, 9815.0, 9810.0, 9805.0, 9800.0,
                9755.0, 9750.0, 9745.0, 9740.0, 9735.0,
                9730.0, 9600.0, 9555.0, 9550.0, 9545.0,
                9540.0, 9535.0, 9530.0, 9525.0, 9520.0,
                9515.0, 9510.0, 9505.0, 9500.0, 9455.0,
                9450.0, 9445.0, 9440.0, 9435.0, 9430.0,
                9425.0, 9420.0, 9415.0, 9410.0, 9405.0,
                9400.0, 10000.0, 9955.0, 9950.0, 9945.0,
                9940.0, 9935.0]
    result = db_session \
        .query(PriceSeq.vals) \
        .filter(PriceSeq.ric == '.TEST',
                PriceSeq.t == '2011-01-14T06:00:00+0000',
                PriceSeq.seqtype == SeqType.MovRefShort.value) \
        .scalar()
    assert allclose(expected, result)


def test_normalized_moving_reference_short(db_session) -> None:
    expected = [-0.960784, -0.963725, -0.964052, -0.964379, -0.964706,
                -0.965033, -0.965359, -0.965686, -0.966013, -0.966340,
                -0.966667, -0.966993, -0.967320, -0.970261, -0.970588,
                -0.970915, -0.971242, -0.971569, -0.971895, -0.972222,
                -0.972549, -0.972876, -0.973203, -0.973529, -0.973856,
                -0.976797, -0.977124, -0.977451, -0.977778, -0.978105,
                -0.978431, -0.986928, -0.989869, -0.990196, -0.990523,
                -0.990850, -0.991176, -0.991503, -0.991830, -0.992157,
                -0.992484, -0.992810, -0.993137, -0.993464, -0.996405,
                -0.996732, -0.997059, -0.997386, -0.997712, -0.998039,
                -0.998366, -0.998693, -0.999020, -0.999346, -0.999673,
                -1.000000, -0.960784, -0.963725, -0.964052, -0.964379,
                -0.964706, -0.965033]
    result = db_session \
        .query(PriceSeq.vals) \
        .filter(PriceSeq.ric == '.TEST',
                PriceSeq.t == '2011-01-14T06:00:00+0000',
                PriceSeq.seqtype == SeqType.NormMovRefShort.value) \
        .scalar()
    assert allclose(expected, result)
