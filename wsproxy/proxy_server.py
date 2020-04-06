from __future__ import annotations

import asyncio
import logging.config
from typing import Optional, NoReturn

import wsproxy.config as cfg
from wsproxy.base_protocol import BaseTcpProtocol, CypherProtocol

logging.config.dictConfig(cfg.logging)
logger = logging.getLogger(__name__)


class RemoteTcpProtocol(BaseTcpProtocol):
    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        super().__init__()
        self.reader = reader
        self.writer = writer


class ProxyServerProtocol(CypherProtocol):
    _MAX_TIMEOUT = 30

    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        super().__init__()
        self.reader = reader
        self.writer = writer

    async def handshake(self) -> Optional[RemoteTcpProtocol]:
        """apply immediately after connection established with client

        :return: remote TCP protocol is successful, None otherwise
        """
        reader, writer = await self.handshake_socks5()
        if reader is None or writer is None:
            return None
        else:
            return RemoteTcpProtocol(reader, writer)

    async def from_remote(self, remote: RemoteTcpProtocol) -> NoReturn:
        while not self.closed:
            data = await remote.recv()
            if data is None:
                break
            await self.send(data)

    async def to_remote(self, remote: RemoteTcpProtocol) -> NoReturn:
        while not self.closed:
            data = await self.recv()
            if data is None:
                break
            await remote.send(data)

    async def exchange_data(self) -> None:
        remote = await self.handshake()
        if not remote:
            await self.close()
            return
        else:
            # Pipe the streams, execution order is uncertain
            # can also use 'await asyncio.gather'
            done, pending = await asyncio.wait(
                [self.from_remote(remote),
                 self.to_remote(remote)],
                timeout=self._MAX_TIMEOUT)
            if pending:
                for p in pending:
                    logger.debug(f'cancelling task: {p}')
                    p.cancel()
            await remote.close()
            await self.close()
            return


def run():
    def handle_client(reader, writer):
        local = ProxyServerProtocol(reader, writer)
        logger.info(f'new client from: {local.peer}')
        return asyncio.ensure_future(local.exchange_data())

    async def service(h: str = cfg.proxy_server['host'],
                      p: int = cfg.proxy_server['port']):
        return await asyncio.start_server(handle_client,
                                          host=h,
                                          port=p,
                                          ssl=None)

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
