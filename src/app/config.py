"""project config"""
import os
import sys
from logging.config import dictConfig

basedir = os.path.abspath(os.path.dirname(__file__))
srcdir = os.path.abspath(os.path.join(basedir, os.pardir))
rootdir = os.path.abspath(os.path.join(srcdir, os.pardir))


class Config:
    # pylint: disable=too-few-public-methods
    """default config"""
    # logging
    LOG_LEVEL = "WARNING"
    LOG_LINE_FORMAT = "%(asctime)s %(levelname)-5s %(threadName)s: %(message)s"
    LOG_DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"

    proxy_server = {
        'host': '0.0.0.0',
        'port': 37777,
        'host_public': '127.0.0.1',
    }

    proxy_client = {
        'host': '127.0.0.1',
        'port': 8888,
    }

    cert = {
        'file': f'{rootdir}/../enigma/cert.pem',
        'key': f'{rootdir}/../enigma/key.pem',
        'pass': '',
    }

    cypher = {
        'key': b'AAE209EBC7168B13761E92C178CBF566',
        'associated': b'10C79942B475CF796A5035303E0C5315',
    }

    @classmethod
    def configure_logger(cls, root_module_name):
        """configure logging"""
        dictConfig({
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "stdout_formatter": {
                    "format": cls.LOG_LINE_FORMAT,
                    "datefmt": cls.LOG_DATETIME_FORMAT,
                },
            },
            "handlers": {
                "stdout_handler": {
                    "level": cls.LOG_LEVEL,
                    "formatter": "stdout_formatter",
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                },
            },
            "loggers": {
                root_module_name: {
                    "handlers": ["stdout_handler"],
                    "level": cls.LOG_LEVEL,
                    "propagate": True,
                },
            },
        })


class TestConfig(Config):
    # pylint: disable=too-few-public-methods
    """testing config"""
    LOG_LEVEL = "DEBUG"
