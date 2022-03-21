"""project config"""
import os
import sys
from logging.config import dictConfig

basedir = os.path.abspath(os.path.dirname(__file__))
srcdir = os.path.abspath(os.path.join(basedir, os.pardir))
rootdir = os.path.abspath(os.path.join(srcdir, os.pardir))


class Config:
    """default config"""

    # certificate
    CERT_FILE = f'{rootdir}/../enigma/cert.pem'
    CERT_KEY = f'{rootdir}/../enigma/key.pem'
    CERT_PASS = ''

    # cypher
    CYPHER_KEY = b'AAE209EBC7168B13761E92C178CBF566'
    CYPHER_ASSO = b'10C79942B475CF796A5035303E0C5315'

    # address
    CLIENT_ADDR = '127.0.0.1'
    CLIENT_PORT = 8888
    REMOTE_HOST_ADDR = '127.0.0.1'
    HOST_ADDR = '0.0.0.0'
    HOST_PORT = 37777

    # logging
    LOG_LEVEL = "WARNING"
    LOG_LINE_FORMAT = "%(asctime)s %(levelname)-5s %(threadName)s: %(message)s"
    LOG_DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"

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
