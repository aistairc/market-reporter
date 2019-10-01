from reporter.core.operation import find_operation, perform_operation


def test_find_operation():

    ref_token = 100
    prev_trading_day_close = 10000
    latest = 10120
    result = find_operation(ref_token, prev_trading_day_close, latest)
    assert result == '<yen val="Δ-round-down-100"/>'


def test_find_operation_reverse():

    ref_token = 100
    prev_trading_day_close = 10120
    latest = 10000
    result = find_operation(ref_token, prev_trading_day_close, latest)
    assert result == '<yen val="Δ-round-down-100"/>'


def test_perform_operation():

    token = '<yen val="Δ-round-down-100"/>'
    prev_trading_day_close = 10000
    latest = 10120
    result = perform_operation(token, prev_trading_day_close, latest)
    assert result == '100円'
