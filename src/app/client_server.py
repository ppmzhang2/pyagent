"""client server"""
from __future__ import annotations

import asyncio
import logging
from ssl import SSLContext
from typing import NoReturn

from .base_protocol import BaseTcpProtocol
from .base_protocol import CypherProtocol

LOGGER = logging.getLogger(__name__)


class ClientRemoteProtocol(CypherProtocol):
    """client remote protocol"""
    _MAX_TIMEOUT = 30

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

    async def to_local(self, local: BaseTcpProtocol) -> NoReturn:
        """get data and send to local"""
        while not self.closed:
            data = await self.recv_block()
            if data is None:
                break
            await local.send(data)

    async def from_local(self, local: BaseTcpProtocol) -> NoReturn:
        """get data from local and send"""
        while not self.closed:
            data = await local.recv()
            if data is None:
                break
            await self.send_block(data)

    async def exchange_data(self, local: BaseTcpProtocol):
        """exchange data"""
        _, pending = await asyncio.wait(
            [self.from_local(local),
             self.to_local(local)],
            timeout=self._MAX_TIMEOUT,
        )
        if pending:
            for p in pending:
                LOGGER.debug(f'cancelling task: {p}')
                p.cancel()
        await self.close()
