from __future__ import annotations

import asyncio
import logging.config
from functools import wraps
from typing import Optional, NoReturn

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
    def __init__(self):
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

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
