import asyncio
import logging.config

import wsproxy.config as cfg

logging.config.dictConfig(cfg.logging)
logger = logging.getLogger(__name__)


class FreeClient(asyncio.Protocol):
    """Client to get free web data

    """
    def __init__(self):
        self.transport = None
        self.server_transport = None

    def connection_made(self, transport):
        logger.info(
            f"`Client` connection made from: {transport.get_extra_info('peername')}"
        )
        self.transport = transport

    def data_received(self, data):
        logger.info(f'client received: {repr(data)}')
        self.server_transport.write(data)

    def connection_lost(self, *args):
        self.server_transport.close()
