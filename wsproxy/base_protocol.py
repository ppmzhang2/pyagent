from __future__ import annotations

import asyncio
import logging.config
from functools import wraps
from typing import Optional, NoReturn

import wsproxy.config as cfg
from wsproxy.enigma import AesGcm

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

    return helper


class BaseTcpProtocol(object):
    __slots__ = ['reader', 'writer']

    reader: Optional[asyncio.StreamReader]
    writer: Optional[asyncio.StreamWriter]

    def __init__(self):
        pass

    @property
    def initiated(self):
        return self.reader is not None and self.writer is not None

    async def recv(self, num: int = 4096) -> Optional[bytes]:
        if not self.initiated:
            return None
        data = await self.reader.read(num)
        if data:
            return data
        else:
            return None

    async def send(self, data: bytes) -> Optional[int]:
        if not self.initiated:
            return None
        self.writer.write(data)
        await self.writer.drain()
        return len(data)

    async def close(self) -> NoReturn:
        if not self.initiated:
            pass
        else:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except ConnectionError:
                pass

    @property
    def closed(self) -> Optional[bool]:
        if not self.initiated:
            return None
        return self.writer.is_closing()


class AesTcpProtocol(BaseTcpProtocol):
    _cypher = AesGcm(key=cfg.cypher['key'],
                     associated=cfg.cypher['associated'])

    async def send(self, data: bytes) -> Optional[int]:
        assert len(data) <= self._cypher.DATA_SIZE
        cypher_block = self._cypher.block_encrypt(data)
        return await super().send(cypher_block)

    async def _recv_block(self, size: int) -> Optional[bytes]:
        data = b''
        diff = size

        while True:
            delta = await super().recv(num=diff)
            if delta is None:
                return
            data += delta
            diff -= len(delta)
            if diff == 0:
                break

        return data

    async def recv(self, **kwargs) -> Optional[bytes]:
        cypher_block = await self._recv_block(self._cypher.FULL_BLOCK_SIZE)
        if not cypher_block:
            logger.debug('data non complete, abort')
            return None
        return self._cypher.block_decrypt(cypher_block)
