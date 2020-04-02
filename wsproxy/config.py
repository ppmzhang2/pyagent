import os

basedir = os.path.abspath(os.path.dirname(__file__))

logging = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'WARNING',
            'propagate': False,
        },
        'my.packg': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False,
        },
        '__main__': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

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
    'file': f'{basedir}/../enigma/cert.pem',
    'key': f'{basedir}/../enigma/key.pem',
    'pass': '',
}

cypher = {
    'key': b'AAE209EBC7168B13761E92C178CBF566',
    'associated': b'10C79942B475CF796A5035303E0C5315',
}
