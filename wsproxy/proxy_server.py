from __future__ import annotations

import asyncio
import logging.config
import socket
from struct import pack, unpack
from typing import Optional, NoReturn, Tuple

import wsproxy.config as cfg
from wsproxy.base_protocol import BaseTcpProtocol, AesTcpProtocol

logging.config.dictConfig(cfg.logging)
logger = logging.getLogger(__name__)


class RemoteTcpProtocol(BaseTcpProtocol):
    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        super().__init__()
        self.reader = reader
        self.writer = writer


class ProxyServerProtocol(AesTcpProtocol):
    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        super().__init__()
        self.reader = reader
        self.writer = writer

    @property
    def peer(self) -> Optional[Tuple[str, int]]:
        """address & port of a peer, from which initiates connection

        :return: a tuple of 1. address; 2. port
        """
        return self.writer.get_extra_info('peername')

    @property
    def sock(self) -> Optional[Tuple[str, int]]:
        """socket binding address & port

        :return: a tuple of 1. address; 2. port
        """
        return self.writer.get_extra_info('sockname')

    async def handshake(self) -> Optional[RemoteTcpProtocol]:
        """apply immediately after connection established with client

        :return: remote TCP protocol is successful, None otherwise
        """
        init_req = await self.recv()
        if not init_req:
            logger.info('handshake failed: no data received')
            return
        elif not init_req[0] == 0x05:
            logger.info('handshake failed: not SOCKS5')
            return
        else:
            pass

        await self.send(pack('!BB', 0x05, 0x00))
        logger.info(f'try to accept {self.peer} with no auth...')

        conn_req = await self.recv()
        ver, cmd, rsv, atype = conn_req[:4]
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
            logger.error(f'handshake failed: AType {atype} not supported')
            return

        port = unpack('!H', conn_req[port_idx:port_idx + 2])[0]

        try:
            reader, writer = await asyncio.open_connection(host=host,
                                                           port=port)
        except ConnectionRefusedError as e:
            logger.error(f'handshake failed: {e}')
            return
        proxy_hostname = unpack(
            "!I", socket.inet_aton(cfg.proxy_server['host_public']))[0]
        respond = pack('!BBBBIH', 0x05, 0x00, 0x00, 0x01, proxy_hostname,
                       cfg.proxy_server['port'])
        await self.send(respond)
        logger.info(f'handshake successful with {self.peer}')
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
            asyncio.ensure_future(self.from_remote(remote))
            asyncio.ensure_future(self.to_remote(remote))
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
