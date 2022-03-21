"""base protocols"""
from __future__ import annotations

import asyncio
import logging
import socket
from functools import wraps
from struct import unpack
from typing import NoReturn
from typing import Optional
from typing import Tuple

from . import cfg
from .enigma import AesGcm

LOGGER = logging.getLogger(__name__)


def dec(fn):
    """error handler decorator"""

    @wraps(fn)
    async def helper(self: BaseTcpProtocol, *args, **kwargs):
        try:
            return await fn(self, *args, **kwargs)
        except (BrokenPipeError, ConnectionResetError, TimeoutError) as e:
            LOGGER.debug(e)
        except Exception as e:
            LOGGER.error(e)
            raise e

    return helper


class BaseTcpProtocol:
    """base TCP protocol"""
    __slots__ = ['reader', 'writer']

    reader: Optional[asyncio.StreamReader]
    writer: Optional[asyncio.StreamWriter]

    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    @staticmethod
    def _inet_aton_int(addr: str) -> int:
        """
        convert an IP address string into binary form with `inet_aton` and
        return its unpakced integer number
        """
        return unpack('!I', socket.inet_aton(addr))[0]

    @property
    def initiated(self) -> bool:
        """object initiated or not"""
        return self.reader is not None and self.writer is not None

    async def _recv(self, size: int = 4096) -> Optional[bytes]:
        if not self.initiated:
            return None
        data = await self.reader.read(size)
        if data:
            return data
        return None

    async def recv(self, size: int = 4096) -> Optional[bytes]:
        """receive data"""
        return await self._recv(size=size)

    async def recv_any(self,
                       size: int = 4096,
                       times: int = 3,
                       interval: float = 0.5) -> Optional[bytes]:
        """try a few times to receive data from the stream reader, and return
          ANY received unless all attempts return None

        :param size: optional, data size for each read
        :param times: optional, #attempts
        :param interval: time interval between each attempt
        :return: first non-None data received, None if no data available
        """
        for _ in range(times):
            data = await self._recv(size=size)
            if data is not None:
                return data
            await asyncio.sleep(interval)
        LOGGER.info('reader is empty')
        return

    async def recv_all(
        self,
        size: int,
        times: int = 3,
        interval: float = 0.5,
    ) -> Optional[bytes]:
        """receive all"""
        data = b''
        diff = size
        while True:
            delta = await self.recv_any(size=diff,
                                        times=times,
                                        interval=interval)
            if not delta:
                return
            data += delta
            diff -= len(delta)
            if diff <= 0:
                break

        return data

    async def send(self, data: bytes) -> Optional[int]:
        """send data"""
        if not self.initiated:
            return None
        self.writer.write(data)
        await self.writer.drain()
        return len(data)

    async def close(self) -> NoReturn:
        """safe close"""
        if not self.initiated:
            pass
        else:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except ConnectionError:
                pass

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

    @property
    def closed(self) -> Optional[bool]:
        """check object closed or not"""
        if not self.initiated:
            return None
        return self.writer.is_closing()


class CypherProtocol(BaseTcpProtocol):
    """encrypted protocol"""
    _cypher = AesGcm(key=cfg.CYPHER_KEY, associated=cfg.CYPHER_ASSO)

    async def send_block(self, data: bytes) -> Optional[int]:
        assert len(data) <= self._cypher.DATA_SIZE
        cypher_block = self._cypher.block_encrypt(data)
        return await super().send(cypher_block)

    async def recv_block(self) -> Optional[bytes]:
        """receive method"""
        cypher_block = await self.recv_all(size=self._cypher.FULL_BLOCK_SIZE)
        if not cypher_block:
            LOGGER.debug('data non complete, abort')
            return None
        return self._cypher.block_decrypt(cypher_block)
