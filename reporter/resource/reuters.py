import logging
import re
import time
from http import HTTPStatus
from logging import Logger
from pathlib import Path
from typing import Dict, List, Union

import requests

from reporter.util.constant import Reuters


def filename2ric(filename: str) -> str:
    """
    >>> filename2ric('/somewhere/_jsd.csv.gz')
    '.JSD'
    >>> filename2ric('/somewhere/eur=.csv.gz')
    'EUR='
    >>> filename2ric('/somewhere/_irail_t.csv.gz')
    '.IRAIL.T'
    >>> filename2ric('/somewhere/jni#c1.csv.gz')
    'JNIc1'
    """

    return re.sub(r'(#[A-Z])',
                  lambda match: match.group(0).replace('#', '').lower(),
                  Path(filename).name.split('.')[0].replace('_', '.').upper())


def ric2filename(dirname: Path, ric: str, extension: str) -> Path:
    """
    >>> ric2filename(Path('/somewhere/'), '.JSD', 'csv.gz')
    PosixPath('/somewhere/_jsd.csv.gz')
    >>> ric2filename(Path('/somewhere/'), 'EUR=', 'csv.gz')
    PosixPath('/somewhere/eur=.csv.gz')
    >>> ric2filename(Path('/somewhere/'), '.IRAIL.T', 'csv.gz')
    PosixPath('/somewhere/_irail_t.csv.gz')
    >>> ric2filename('/somewhere/', 'JNIc1', 'csv.gz')
    PosixPath('/somewhere/jni#c1.csv.gz')
    """

    basename = re.sub(r'([a-z])', r'#\1', ric).lower().replace('.', '_')
    sanitized_basename = re.sub('[^a-z0-9_#=]', '', basename)
    return dirname / Path(sanitized_basename + '.' + extension)


def download_prices_from_reuters(username: str,
                                 password: str,
                                 dest_dir: Path,
                                 rics: List[str],
                                 logger: Logger = None,
                                 start: str = None,
                                 end: str = None) -> None:

    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.CRITICAL)

    dest_dir.mkdir(parents=True, exist_ok=True)
    auth_token = get_auth_token(username, password)
    header = make_extract_header(auth_token)

    todo = [{
            'ric': ric,
            'uri': Reuters.extraction_raw_uri,
            'file': ric2filename(dest_dir, ric, 'csv.gz')
            } for ric in rics]
    todo = [item for item in todo if not item['file'].is_file()]
    for item in todo:
        logging.info('start downloading {} from Reuters'.format(item['ric']))
        item['json'] = make_payload(item['ric'], start=start, end=end)

    while todo:
        future = []
        for item in todo:
            if item['json']:
                r = requests.post(item['uri'],
                                  data=None,
                                  json=item['json'],
                                  headers=header)
            else:
                r = requests.get(item['uri'],
                                 headers=header)
            if r.status_code == HTTPStatus.OK.value:
                job_id = r.json().get('JobId')
                results_uri = Reuters.raw_extraction_results_uri.format(job_id)
                r = requests.get(results_uri, headers=header, stream=True)

                with item['file'].open(mode='wb') as f:
                    f.write(r.raw.read())

                logging.info('end downloading {} from Reuters'.format(item['ric']))

            elif r.status_code == HTTPStatus.ACCEPTED.value:
                item['uri'] = r.headers['Location']
                item['json'] = None
                future.append(item)

                logging.debug('waiting for {} from Reuters'.format(item['ric']))

            else:
                logging.error('error downloading {} from Reuters: {}'.format(item['ric'], r.status_code))

        time.sleep(10)
        todo = future

    logging.info('all download requests finished')


def get_auth_token(username: str, password: str) -> Union[None, str]:

    uri = Reuters.auth_token_uri
    header = \
        {
            'Prefer': 'respond-async',
            'Content-Type': 'application/json'
        }
    auth = {'Username': username, 'Password': password}
    data = {'Credentials': auth}

    response = requests.post(uri, json=data, headers=header)

    if response.status_code == HTTPStatus.OK.value:
        auth_token = response.json()['value']
        return auth_token
    else:
        logging.error('error authenticating with Reuters: {}'.format(response.status_code))
        return None


def make_extract_header(auth_token: str) -> Dict[str, str]:
    return \
        {
            'Prefer': 'respond-async',
            'Content-Type': 'application/json',
            'Accept-Charset': 'UTF-8',
            'Authorization': 'Token ' + auth_token
        }


def make_payload(ric: str, start: str = None, end: str = None) \
        -> Dict[str, Dict[str, Union[str, Dict[str, Union[str, bool]]]]]:

    content_field_names = \
        [
            'Open',
            'High',
            'Low',
            'Last',
            'Volume',
            'No. Trades',
            'Open Bid',
            'High Bid',
            'No. Bids',
            'Close Bid',
            'Low Bid',
            'Open Ask',
            'High Ask',
            'Low Ask',
            'Close Ask'
        ]

    instruments = [{'IdentifierType': 'Ric', 'Identifier': ric}]

    odata_type_prefix = \
        '.'.join(['#ThomsonReuters',
                  'Dss',  # DataScope Select
                  'Api',
                  'Extractions',
                  'ExtractionRequests'])
    tick_history = \
        '.'.join([odata_type_prefix,
                  'TickHistoryIntradaySummariesExtractionRequest'])
    instrument_identifier_list = \
        '.'.join([odata_type_prefix,
                  'InstrumentIdentifierList'])

    validation_options = \
        {
            'AllowOpenAccessInstruments': True,
            'AllowHistoricalInstruments': True,
            'AllowLimitedTermInstruments': True,
            'ExcludeFinrAsPricingSourceForBonds': True,
            'UseExchangeCodeInsteadOfLipper': True,
            'UseUsQuoteInsteadOfCanadian': True,
            'UseConsolidatedQuoteSourceForUsa': True,
            'UseConsolidatedQuoteSourceForCanada': True,
            'UseDebtOverEquity': True
        }

    condition = \
        {
            'MessageTimeStampIn': 'GmtUtc',
            'ReportDateRangeType': 'Range',
            'QueryStartDate': start or Reuters.start,
            'QueryEndDate': end or Reuters.end,
            'SummaryInterval': 'FiveMinutes',
            'ExtractBy': 'Entity',
            'TimebarPersistence': True,
            'DisplaySourceRIC': True
        }

    payload = \
        {
            'ExtractionRequest': {
                '@odata.type': tick_history,
                'ContentFieldNames': content_field_names,
                'IdentifierList': {
                    '@odata.type': instrument_identifier_list,
                    'InstrumentIdentifiers': instruments,
                    'ValidationOptions': validation_options,
                    'UseUserPreferencesForValidationOptions': False
                },
                'Condition': condition
            }
        }
    return payload
