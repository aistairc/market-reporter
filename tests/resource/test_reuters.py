from unittest import TestCase
from pathlib import Path

import toml

from reporter.resource.reuters import get_auth_token, filename2ric, ric2filename


class TestReuters(TestCase):

    def setUp(self):

        self.username = None
        self.password = None

        dest_secret = Path('.secret.toml')
        if dest_secret.is_file():
            with dest_secret.open(mode='r') as f:
                config = toml.load(f)
                self.username = config.get('reuters', {}).get('username')
                self.password = config.get('reuters', {}).get('password')

    def test_get_auth_token(self):

        if self.username is None or self.password is None:
            self.skipTest('No Authentication Information')
        else:
            auth_token = get_auth_token(self.username, self.password)
            self.assertIsNotNone(auth_token)

    def test_filename2ric_period(self):
        result = filename2ric('/somewhere/_jsd.csv.gz')
        expected = '.JSD'
        self.assertEqual(result, expected)

    def test_filename2ric_equql(self):
        result = filename2ric('/somewhere/eur=.csv.gz')
        expected = 'EUR='
        self.assertEqual(result, expected)

    def test_filename2ric_underscore(self):
        result = filename2ric('/somewhere/_irail_t.csv.gz')
        expected = '.IRAIL.T'
        self.assertEqual(result, expected)

    def test_filename2ric_lowercase(self):
        result = filename2ric('/somewhere/jni#c1.csv.gz')
        expected = 'JNIc1'
        self.assertEqual(result, expected)

    def test_ric2filename_period(self):
        result = ric2filename(Path('/somewhere/'), '.JSD', 'csv.gz')
        expected = Path('/somewhere/_jsd.csv.gz')
        self.assertEqual(result, expected)

    def test_ric2filename_equal(self):
        result = ric2filename(Path('/somewhere/'), 'EUR=', 'csv.gz')
        expected = Path('/somewhere/eur=.csv.gz')
        self.assertEqual(result, expected)

    def test_ric2filename_underscore(self):
        result = ric2filename(Path('/somewhere/'), '.IRAIL.T', 'csv.gz')
        expected = Path('/somewhere/_irail_t.csv.gz')
        self.assertEqual(result, expected)

    def test_ric2filename_lowercase(self):
        result = ric2filename(Path('/somewhere/'), 'JNIc1', 'csv.gz')
        expected = Path('/somewhere/jni#c1.csv.gz')
        self.assertEqual(result, expected)
