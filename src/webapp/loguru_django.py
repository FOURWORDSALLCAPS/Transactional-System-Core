import logging
import sys

from loguru import logger


class LoguruInterceptHandler(logging.Handler):
    LEVELS_MAP = {
        logging.CRITICAL: "CRITICAL",
        logging.ERROR: "ERROR",
        logging.WARNING: "WARNING",
        logging.INFO: "INFO",
        logging.DEBUG: "DEBUG",
    }

    def _get_level(self, record: logging.LogRecord) -> str:
        return self.LEVELS_MAP.get(record.levelno, str(record.levelno))

    def emit(self, record: logging.LogRecord) -> None:
        logger_opt = logger.opt(depth=6, exception=record.exc_info)
        logger_opt.log(self._get_level(record), record.getMessage())


def configure_logger() -> None:
    logger.remove()
    level = "INFO"

    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD at HH:mm:ss}</green> | <level>{level}</level> | {file}:{line} | "
        "{message}",
        level=level,
    )

    logging.basicConfig(handlers=[LoguruInterceptHandler()], level=logging.INFO)


configure_logger()
