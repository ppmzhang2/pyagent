from __future__ import annotations

import asyncio
import logging.config
import socket
from functools import wraps
from struct import pack, unpack
from typing import Optional, NoReturn, Tuple

import wsproxy.config as cfg

logging.config.dictConfig(cfg.logging)
logger = logging.getLogger(__name__)


def dec(fn):
    @wraps(fn)
    async def helper(self: BaseTcpProtocol, *args, **kwargs):
        try:
            return await fn(self, *args, **kwargs)
        except (BrokenPipeError, ConnectionResetError, TimeoutError) as e:
            logger.debug(e)
        except Exception as e:
            logger.error(e)
            raise e
        finally:
            await self.close()

    return helper


class BaseTcpProtocol(object):
    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    @staticmethod
    async def create_connection(host: str, port: int) -> BaseTcpProtocol:
        """create a TCP socket

        :param host:
        :param port:
        :return:
        """
        reader, writer = await asyncio.open_connection(host=host, port=port)
        return BaseTcpProtocol(reader, writer)

    async def recv(self, num: int = 4096) -> Optional[bytes]:
        data = await self.reader.read(num)
        if data:
            return data
        else:
            return None

    async def send(self, data: bytes) -> int:
        self.writer.write(data)
        await self.writer.drain()
        return len(data)

    async def close(self) -> NoReturn:
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except ConnectionError:
            pass

    @property
    def closed(self) -> bool:
        return self.writer.is_closing()


class RemoteTcpProtocol(BaseTcpProtocol):
    _INIT, _CONN, _DATA = 0, 1, 2

    def __init__(self):
        self.reader = None
        self.writer = None
        self._state = self._INIT

    @property
    def init_phase(self):
        return self._state == self._INIT

    @property
    def conn_phase(self):
        return self._state == self._CONN

    @property
    def data_phase(self):
        return self._state == self._DATA

    async def change_state(self, local: ServerProtocol) -> NoReturn:
        data = await local.recv()
        if self.init_phase:
            assert data[0] == 0x05
            # no auth
            await local.send(pack('!BB', 0x05, 0x00))
            self._state = self._CONN
        elif self.conn_phase:
            ver, cmd, rsv, atype = data[:4]
            assert ver == 0x05 and cmd == 0x01

            if atype == 3:  # domain
                length = data[4]
                host, nxt = data[5:5 + length], 5 + length
            elif atype == 1:  # ipv4
                host, nxt = socket.inet_ntop(socket.AF_INET, data[4:8]), 8
            elif atype == 4:  # ipv6
                host, nxt = socket.inet_ntop(socket.AF_INET6, data[4:20]), 20
            else:
                raise ValueError("type specified not supported")
            port = unpack('!H', data[nxt:nxt + 2])[0]
            reader, writer = await asyncio.open_connection(host=host,
                                                           port=port)
            local_host, local_port = local.sock
            local_hostname = unpack("!I", socket.inet_aton(local_host))[0]

            self.reader = reader
            self.writer = writer
            self._state = self._DATA
            await local.send(
                pack('!BBBBIH', 0x05, 0x00, 0x00, 0x01, local_hostname,
                     local_port))
        else:
            pass

    @dec
    async def remote_to_local(self, local: ServerProtocol) -> NoReturn:
        if self.data_phase:
            while True:
                data = await self.recv()
                if data is None:
                    break
                await local.send(data)
        else:
            pass

    @dec
    async def local_to_remote(self, local: ServerProtocol) -> NoReturn:
        if self.data_phase:
            while True:
                data = await local.recv()
                if data is None:
                    break
                await self.send(data)


class ServerProtocol(BaseTcpProtocol):
    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        super().__init__(reader, writer)

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

    async def exchange_data(self):
        remote = RemoteTcpProtocol()
        while not remote.data_phase:
            await remote.change_state(self)
        # Pipe the streams, execution order is uncertain
        # can also use 'await asyncio.gather'
        asyncio.ensure_future(remote.local_to_remote(self))
        asyncio.ensure_future(remote.remote_to_local(self))


def run(host: str = '127.0.0.1', port: int = 1080):
    def handle_client(reader, writer):
        local = ServerProtocol(reader, writer)
        logger.debug(f'initiated from: {local.peer}')
        return asyncio.ensure_future(local.exchange_data())

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
    run()
