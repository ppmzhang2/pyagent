from __future__ import annotations

import asyncio
import logging.config
from typing import NoReturn

import wsproxy.config as cfg
from wsproxy.base_protocol import BaseTcpProtocol, dec

logging.config.dictConfig(cfg.logging)
logger = logging.getLogger(__name__)


class ClientRemoteProtocol(BaseTcpProtocol):
    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        super().__init__()
        self.reader = reader
        self.writer = writer

    @staticmethod
    async def create_connection(proxy_host: str,
                                proxy_port: int) -> ClientRemoteProtocol:
        """connect to a proxy server and initiate the remote connection

        :param proxy_host: proxy host name
        :param proxy_port: proxy port
        :return:
        """
        reader, writer = await asyncio.open_connection(host=proxy_host,
                                                       port=proxy_port)
        return ClientRemoteProtocol(reader, writer)

    @dec
    async def remote_to_local(self, local: ClientServerProtocol) -> NoReturn:
        if self.initiated:
            while True:
                data = await self.recv()
                if data is None:
                    break
                await local.send(data)

    @dec
    async def local_to_remote(self, local: ClientServerProtocol) -> NoReturn:
        if self.initiated:
            while True:
                data = await local.recv()
                if data is None:
                    break
                await self.send(data)


class ClientServerProtocol(BaseTcpProtocol):
    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        super().__init__()
        self.reader = reader
        self.writer = writer

    async def exchange_data(self, remote: ClientRemoteProtocol):
        if self.initiated:
            asyncio.ensure_future(remote.local_to_remote(self))
            asyncio.ensure_future(remote.remote_to_local(self))


def run(proxy_host: str,
        proxy_port: int,
        host: str = '127.0.0.1',
        port: int = 8888):
    async def handle_client(reader, writer):
        local = ClientServerProtocol(reader, writer)
        remote = await ClientRemoteProtocol.create_connection(
            proxy_host, proxy_port)
        return asyncio.ensure_future(local.exchange_data(remote))

    async def service(h: str, p: int):
        return await asyncio.start_server(handle_client, host=h, port=p)

    loop = asyncio.get_event_loop()
    server = loop.run_until_complete(service(host, port))

    for s in server.sockets:
        logger.info('Proxy broker listening on {}'.format(s.getsockname()))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()


if __name__ == '__main__':
    run('127.0.0.1', 1080)
