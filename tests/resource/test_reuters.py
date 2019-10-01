from pathlib import Path

import pytest

import toml
from reporter.resource.reuters import (
    filename2ric,
    get_auth_token,
    ric2filename
)


def test_get_auth_token():

    username = None
    password = None

    dest_secret = Path('.secret.toml')
    if dest_secret.is_file():
        with dest_secret.open(mode='r') as f:
            config = toml.load(f)
            username = config.get('reuters', {}).get('username')
            password = config.get('reuters', {}).get('password')

    if username is None or password is None:
        pytest.skip('No Authentication Information')
    else:
        auth_token = get_auth_token(username, password)
        pytest.skip(auth_token)


def test_filename2ric_period():
    result = filename2ric('/somewhere/_jsd.csv.gz')
    expected = '.JSD'
    assert result == expected


def test_filename2ric_equql():
    result = filename2ric('/somewhere/eur=.csv.gz')
    expected = 'EUR='
    assert result == expected


def test_filename2ric_underscore():
    result = filename2ric('/somewhere/_irail_t.csv.gz')
    expected = '.IRAIL.T'
    assert result == expected


def test_filename2ric_lowercase():
    result = filename2ric('/somewhere/jni#c1.csv.gz')
    expected = 'JNIc1'
    assert result == expected


def test_ric2filename_period():
    result = ric2filename(Path('/somewhere/'), '.JSD', 'csv.gz')
    expected = Path('/somewhere/_jsd.csv.gz')
    assert result == expected


def test_ric2filename_equal():
    result = ric2filename(Path('/somewhere/'), 'EUR=', 'csv.gz')
    expected = Path('/somewhere/eur=.csv.gz')
    assert result == expected


def test_ric2filename_underscore():
    result = ric2filename(Path('/somewhere/'), '.IRAIL.T', 'csv.gz')
    expected = Path('/somewhere/_irail_t.csv.gz')
    assert result == expected


def test_ric2filename_lowercase():
    result = ric2filename(Path('/somewhere/'), 'JNIc1', 'csv.gz')
    expected = Path('/somewhere/jni#c1.csv.gz')
    assert result == expected
