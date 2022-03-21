"""proxy server"""
from __future__ import annotations

import asyncio
import logging
import socket
from struct import pack
from struct import unpack
from typing import NoReturn
from typing import Optional

from . import cfg
from .base_protocol import BaseTcpProtocol
from .base_protocol import CypherProtocol

LOGGER = logging.getLogger(__name__)


class ProxyServerProtocol(CypherProtocol):
    """proxy server protocol"""

    _MAX_TIMEOUT = 30

    async def handshake_socks5(self) -> Optional[BaseTcpProtocol]:
        """handshake handler for socks5 protocol

        :return: a BaseTcpProtocol instance if handshake successful, None
            otherwise
        """
        init_req = await self.recv_block()
        if not init_req:
            LOGGER.info('handshake failed: no data received')
            return
        if not init_req[0] == 0x05:
            LOGGER.info('handshake failed: not SOCKS5')
            return

        await self.send_block(pack('!BB', 0x05, 0x00))
        LOGGER.info(f'try to accept {self.peer} with no auth...')

        conn_req = await self.recv_block()
        ver, cmd, _, atype = conn_req[:4]
        assert ver == 0x05 and cmd == 0x01

        if atype == 3:  # domain
            url_len = conn_req[4]
            host, port_idx = conn_req[5:5 + url_len], 5 + url_len
        elif atype == 1:  # ipv4
            host, port_idx = socket.inet_ntop(socket.AF_INET, conn_req[4:8]), 8
        elif atype == 4:  # ipv6
            host, port_idx = socket.inet_ntop(socket.AF_INET6,
                                              conn_req[4:20]), 20
        else:
            LOGGER.error(f'handshake failed: AType {atype} not supported')
            return

        port = unpack('!H', conn_req[port_idx:port_idx + 2])[0]

        try:
            reader, writer = await asyncio.open_connection(host=host,
                                                           port=port)
        except ConnectionRefusedError as e:
            LOGGER.error(f'handshake failed: {e}')
            return
        LOGGER.info(f'connection established with {host}:{port}')
        respond = pack('!BBBBIH', 0x05, 0x00, 0x00, 0x01,
                       self._inet_aton_int(cfg.REMOTE_HOST_ADDR),
                       cfg.HOST_PORT)
        await self.send_block(respond)
        if reader is None or writer is None:
            return None
        LOGGER.info(f'handshake successful with {self.peer}')
        return BaseTcpProtocol(reader, writer)

    async def from_remote(self, remote: BaseTcpProtocol) -> NoReturn:
        """get data from remote and send"""
        while not self.closed:
            data = await remote.recv()
            if data is None:
                break
            await self.send_block(data)

    async def to_remote(self, remote: BaseTcpProtocol) -> NoReturn:
        """receive data and send to remote"""
        while not self.closed:
            data = await self.recv_block()
            if data is None:
                break
            await remote.send(data)

    async def exchange_data(self) -> None:
        """exchange data"""
        remote = await self.handshake_socks5()
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
