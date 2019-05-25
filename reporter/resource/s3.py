import logging
import os
import re
import zipfile
from http import HTTPStatus
from pathlib import Path
from typing import List

from boto3.resources.base import ServiceResource
from botocore.exceptions import ClientError

from reporter.resource.reuters import filename2ric, ric2filename


def download_nikkei_headlines_from_s3(bucket: ServiceResource,
                                      cp932zip_dirname: str,
                                      utf8csv_dirname: str,
                                      remote_filenames: List[str],
                                      logger: logging.Logger) -> None:

    os.makedirs(cp932zip_dirname, exist_ok=True)
    os.makedirs(utf8csv_dirname, exist_ok=True)

    for remote_filename in remote_filenames:

        basename = os.path.basename(remote_filename).lower()
        temp_dest = os.path.join(cp932zip_dirname, basename)

        if os.path.isfile(temp_dest):
            logger.debug('skip downloading {}'.format(basename))
        else:
            logger.debug('start downloading {}'.format(basename))
            try:
                bucket.download_file(Key=remote_filename, Filename=temp_dest)
            except ClientError as e:
                code = e.response.get('Error', {}).get('Code', '')
                if str(code) == str(HTTPStatus.NOT_FOUND.value):
                    logger.info('{} is not found'.format(remote_filename))
            logger.debug('end downloading {}'.format(basename))

        infl_filename = re.sub(r'\.zip$', '.csv',
                               basename,
                               flags=re.IGNORECASE)
        match = re.search(r'_([12][0-9]{3})_', infl_filename)
        if match is None:
            raise ValueError
        year = int(match[1])
        utf8_filename = os.path.join(utf8csv_dirname,
                                     'nikkei_headlines_{}.csv'.format(year))

        if os.path.isfile(utf8_filename):
            logger.debug('skip converting {}'.format(utf8_filename))
            continue

        with zipfile.ZipFile(temp_dest, mode='r') as zf:

            logger.debug('start converting {}'.format(utf8_filename))

            with zf.open(infl_filename, mode='r') as cp932_file:
                text = cp932_file.read()

            with open(utf8_filename, mode='wb') as utf8_file:
                utf8_file.write(text.decode('cp932').encode('utf-8'))

            logger.debug('end converting {}'.format(utf8_filename))


def download_prices_from_s3(bucket: ServiceResource,
                            dir_prices: Path,
                            remote_dir_prices: Path,
                            missing_rics: List[str],
                            logger: logging.Logger) -> None:

    dir_prices.mkdir(parents=True, exist_ok=True)

    for ric in missing_rics:

        remote_filename = ric2filename(remote_dir_prices, ric, 'csv.gz')

        basename = remote_filename.name
        dest_parent = dir_prices
        dest = dest_parent / Path(basename)

        if dest.is_file():
            logger.debug('skip downloading {}'.format(basename))
        else:
            logger.debug('start downloading {}'.format(basename))
            try:
                bucket.download_file(Key=str(remote_filename), Filename=str(dest))
            except ClientError as e:
                code = e.response.get('Error', {}).get('Code', '')
                if str(code) == str(HTTPStatus.NOT_FOUND.value):
                    logger.critical('{} is not found'.format(str(remote_filename)))
            logger.debug('end downloading {}'.format(basename))


def list_rics_in_s3(bucket: ServiceResource, dirname: str) -> List[str]:
    summaries = bucket.objects.filter(Prefix=dirname).all()
    return [filename2ric(summary.key) for summary in summaries
            if not summary.key.endswith('/')]


def upload_prices_to_s3(bucket: ServiceResource,
                        local_dir: Path,
                        remote_dir: Path,
                        rics: List[str]) -> None:

    for ric in rics:

        local_filename = ric2filename(local_dir, ric, 'csv.gz')

        key = str(remote_dir / Path(local_filename.name))

        objs = list(bucket.objects.filter(Prefix=key).all())

        if len(objs) > 0 and objs[0].key == key:
            continue

        with local_filename.open(mode='rb') as body:

            bucket.put_object(Key=key, Body=body)


def download_reuters_articles_from_s3(bucket: ServiceResource,
                                      dest_dirname: Path,
                                      remote_dirnames: List[Path],
                                      logger: logging.Logger) -> None:

    dest_dirname.mkdir(parents=True, exist_ok=True)
    for remote_dirname in remote_dirnames:
        logger.info('start downloading files in {}'.format(remote_dirname))
        summaries = bucket.objects.filter(Prefix=str(remote_dirname))
        for summary in summaries:
            dest = Path(dest_dirname).joinpath(summary.key.split('/')[-1])
            if not summary.key.endswith('/') and not dest.is_file():
                bucket.download_file(Key=summary.key, Filename=str(dest))
        logger.info('end downloading files in {}'.format(remote_dirname))


def download_nikkei_bodies_from_s3(bucket: ServiceResource,
                                   dest_dirname: Path,
                                   remote_filenames: List[Path],
                                   logger: logging.Logger) -> None:

    dest_dirname.mkdir(parents=True, exist_ok=True)
    for remote_filename in remote_filenames:
        logger.info('start downloading {}'.format(remote_filename))
        dest = dest_dirname.joinpath(remote_filename.name)
        if not dest.is_file():
            bucket.download_file(Key=str(remote_filename), Filename=str(dest))
        logger.info('start downloading {}'.format(remote_filename))
