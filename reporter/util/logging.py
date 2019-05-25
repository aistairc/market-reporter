import logging
import logging.config
from pathlib import Path


def create_logger(dest_log: Path, is_debug: bool, is_temporary: bool = False) -> logging.Logger:

    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    FORMAT = '%(asctime)s %(levelname)s %(message)s'

    dest_log.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(__name__)
    logging.basicConfig()

    level = logging.DEBUG if is_debug else logging.INFO
    logger.setLevel(level)
    logger.propagate = False

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)

    stream_handler.setFormatter(logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(stream_handler)

    if not is_temporary:
        file_handler = logging.FileHandler(filename=str(dest_log), mode='w')
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(file_handler)

    return logger
