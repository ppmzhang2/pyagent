from __future__ import annotations

import asyncio
import logging.config
from ssl import SSLContext
from typing import NoReturn

import pyagent.config as cfg
from pyagent.base_protocol import BaseTcpProtocol, CypherProtocol

logging.config.dictConfig(cfg.logging)
logger = logging.getLogger(__name__)


class ClientRemoteProtocol(CypherProtocol):
    _MAX_TIMEOUT = 30

    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        super().__init__()
        self.reader = reader
        self.writer = writer

    @staticmethod
    async def create_connection(
            proxy_host: str,
            proxy_port: int,
            ssl: SSLContext = None) -> ClientRemoteProtocol:
        """connect to a proxy server and initiate the remote connection

        :param proxy_host: proxy host name
        :param proxy_port: proxy port
        :param ssl: SSL context for proxy server
        :return:
        """
        reader, writer = await asyncio.open_connection(host=proxy_host,
                                                       port=proxy_port,
                                                       ssl=ssl)
        return ClientRemoteProtocol(reader, writer)

    async def to_local(self, local: ClientServerProtocol) -> NoReturn:
        while not self.closed:
            data = await self.recv()
            if data is None:
                break
            await local.send(data)

    async def from_local(self, local: ClientServerProtocol) -> NoReturn:
        while not self.closed:
            data = await local.recv()
            if data is None:
                break
            await self.send(data)

    async def exchange_data(self, local: ClientServerProtocol):
        done, pending = await asyncio.wait(
            [self.from_local(local),
             self.to_local(local)],
            timeout=self._MAX_TIMEOUT)
        if pending:
            for p in pending:
                logger.debug(f'cancelling task: {p}')
                p.cancel()
        await self.close()


class ClientServerProtocol(BaseTcpProtocol):
    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        super().__init__()
        self.reader = reader
        self.writer = writer


def run():
    async def handle_client(reader, writer):
        local = ClientServerProtocol(reader, writer)
        remote = await ClientRemoteProtocol.create_connection(
            cfg.proxy_server['host_public'], cfg.proxy_server['port'])
        return asyncio.ensure_future(remote.exchange_data(local))

    async def service(h: str = cfg.proxy_client['host'],
                      p: int = cfg.proxy_client['port']):
        return await asyncio.start_server(handle_client, host=h, port=p)

    loop = asyncio.get_event_loop()
    server = loop.run_until_complete(service())

    for s in server.sockets:
        logger.info('Proxy broker listening on {}'.format(s.getsockname()))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
