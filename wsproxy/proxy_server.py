import asyncio
import logging.config
import socket
from struct import pack, unpack
from typing import Tuple

import wsproxy.config as cfg
from wsproxy.free_client import FreeClient

logging.config.dictConfig(cfg.logging)
logger = logging.getLogger(__name__)


class ProxyServer(asyncio.Protocol):
    INIT, HOST, DATA = 0, 1, 2

    def __init__(self):
        self.transport = None
        self.browser_transport = None
        self.state = self.INIT

    def connection_made(self, transport):
        logger.info(
            f"`Server` connection made from: {transport.get_extra_info('peername')}"
        )
        self.transport = transport

    def connection_lost(self, exc):
        self.transport.close()

    def data_received(self, data):
        logger.info(f'server received: {data}')
        nxt = None
        hostname = None

        if self.state == self.INIT:
            assert data[0] == 0x05
            self.transport.write(pack('!BB', 0x05, 0x00))  # no auth
            self.state = self.HOST

        elif self.state == self.HOST:
            ver, cmd, rsv, atype = data[:4]
            assert ver == 0x05 and cmd == 0x01

            if atype == 3:  # domain
                length = data[4]
                hostname, nxt = data[5:5 + length], 5 + length
            elif atype == 1:  # ipv4
                hostname, nxt = socket.inet_ntop(socket.AF_INET, data[4:8]), 8
            elif atype == 4:  # ipv6
                hostname, nxt = socket.inet_ntop(socket.AF_INET6,
                                                 data[4:20]), 20
            port = unpack('!H', data[nxt:nxt + 2])[0]

            logger.info(f'to: {hostname}: {port}')
            asyncio.ensure_future(self.connect(hostname, port))
            self.state = self.DATA

        elif self.state == self.DATA:
            self.browser_transport.write(data)

    async def connect(self, hostname, port):
        event_loop = asyncio.get_event_loop()
        web_transport, free_client = await create_connection_direct(
            event_loop, FreeClient, hostname, port)
        free_client.server_transport = self.transport
        self.browser_transport = web_transport
        host_ip, port = web_transport.get_extra_info('sockname')
        host = unpack("!I", socket.inet_aton(host_ip))[0]
        self.transport.write(
            pack('!BBBBIH', 0x05, 0x00, 0x00, 0x01, host, port))


async def create_connection_direct(
        event_loop, client, host_name,
        port_num) -> Tuple[asyncio.Transport, FreeClient]:
    return await event_loop.create_connection(client, host_name, port_num)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    srv = loop.create_server(ProxyServer, 'localhost', 1080)
    loop.run_until_complete(srv)
    loop.run_forever()
