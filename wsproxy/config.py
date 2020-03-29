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

server = {
    'host': 'localhost',
    'port': 37777,
}
