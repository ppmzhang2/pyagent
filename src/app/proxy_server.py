"""proxy server"""
from __future__ import annotations

import asyncio
import logging
from typing import NoReturn
from typing import Optional

from . import cfg
from .base_protocol import BaseTcpProtocol
from .base_protocol import CypherProtocol

LOGGER = logging.getLogger(__name__)


class RemoteTcpProtocol(BaseTcpProtocol):
    """remote TCP protocol"""

    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        super().__init__()
        self.reader = reader
        self.writer = writer


class ProxyServerProtocol(CypherProtocol):
    """proxy server protocol"""

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
        return RemoteTcpProtocol(reader, writer)

    async def from_remote(self, remote: RemoteTcpProtocol) -> NoReturn:
        """get data from remote and send"""
        while not self.closed:
            data = await remote.recv()
            if data is None:
                break
            await self.send(data)

    async def to_remote(self, remote: RemoteTcpProtocol) -> NoReturn:
        """receive data and send to remote"""
        while not self.closed:
            data = await self.recv()
            if data is None:
                break
            await remote.send(data)

    async def exchange_data(self) -> None:
        """exchange data"""
        remote = await self.handshake()
        if not remote:
            await self.close()
            return
        # Pipe the streams, execution order is uncertain
        # can also use 'await asyncio.gather'
        _, pending = await asyncio.wait(
            [self.from_remote(remote),
             self.to_remote(remote)],
            timeout=self._MAX_TIMEOUT,
        )
        if pending:
            for p in pending:
                LOGGER.debug(f'cancelling task: {p}')
                p.cancel()
        await remote.close()
        await self.close()
        return


def run():
    """run it"""

    def handle_client(reader, writer):
        local = ProxyServerProtocol(reader, writer)
        LOGGER.info(f'new client from: {local.peer}')
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
        LOGGER.info(f'Proxy broker listening on {s.getsockname()}')

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
