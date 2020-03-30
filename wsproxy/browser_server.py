from __future__ import annotations

import asyncio
import logging.config
from functools import wraps

import wsproxy.config as cfg

logging.config.dictConfig(cfg.logging)
logger = logging.getLogger(__name__)


def dec(fn):
    @wraps(fn)
    async def helper(self: BrowserServer, *args, **kwargs):
        try:
            return await fn(self, *args, **kwargs)
        except Exception as e:
            logger.error(e.__str__())
            raise e
        finally:
            await self.close()

    return helper


class BrowserServer(object):
    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    @staticmethod
    async def create_connection(host: str, port: int) -> BrowserServer:
        """create a TCP socket

        :param host:
        :param port:
        :return:
        """
        reader, writer = await asyncio.open_connection(host=host, port=port)
        return BrowserServer(reader, writer)

    async def recv(self, num: int = 4096) -> bytes:
        data = await self.reader.read(num)
        return data

    async def send(self, data: bytes) -> int:
        self.writer.write(data)
        await self.writer.drain()
        return len(data)

    async def close(self) -> None:
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except ConnectionError:
            pass

    @property
    def closed(self) -> bool:
        return self.writer.is_closing()

    @dec
    async def send_all(self, src: BrowserServer):
        while True:
            data = await src.recv()
            if not data:
                break
            await self.send(data)

    async def exchange_data(self, remote: BrowserServer):
        data = await self.recv()
        # Write the data to remote
        await remote.send(data)
        # Pipe the streams
        asyncio.ensure_future(remote.send_all(self))
        asyncio.ensure_future(self.send_all(remote))

    @staticmethod
    def run():
        async def handle_client(reader, writer):
            local = BrowserServer(reader, writer)
            remote = await BrowserServer.create_connection(host='127.0.1',
                                                           port=1080)
            return asyncio.ensure_future(local.exchange_data(remote))

        async def service(host: str = '127.0.0.1', port: int = 8888):
            return await asyncio.start_server(handle_client,
                                              host=host,
                                              port=port)

        try:
            loop = asyncio.get_event_loop()
            server = loop.run_until_complete(service())
        except Exception as e:
            logger.error('Bind error: {}'.format(e))
            raise e

        for s in server.sockets:
            logger.info('Proxy broker listening on {}'.format(s.getsockname()))

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    BrowserServer.run()
