from helpers.logger import logger


def raise_error(message: str) -> None:
    logger.error(message)
    raise Exception(message)
