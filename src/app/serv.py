"""server / client services"""
import asyncio
import logging

import click

from . import cfg
from .base_protocol import BaseTcpProtocol
from .client_server import ClientRemoteProtocol
from .proxy_server import ProxyServerProtocol

LOGGER = logging.getLogger(__name__)


@click.command()
def run_client():
    """run client"""

    async def handle_client(reader, writer):
        local = BaseTcpProtocol(reader, writer)
        remote = await ClientRemoteProtocol.create_connection(
            cfg.REMOTE_HOST_ADDR, cfg.HOST_PORT)
        return asyncio.ensure_future(remote.exchange_data(local))

    async def service(h: str = cfg.CLIENT_ADDR, p: int = cfg.CLIENT_PORT):
        return await asyncio.start_server(handle_client, host=h, port=p)

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


@click.command()
def run_server():
    """run server"""

    def handle_client(reader, writer):
        local = ProxyServerProtocol(reader, writer)
        LOGGER.info(f'new client from: {local.peer}')
        return asyncio.ensure_future(local.exchange_data())

    async def service(h: str = cfg.HOST_ADDR, p: int = cfg.HOST_PORT):
        return await asyncio.start_server(
            handle_client,
            host=h,
            port=p,
            ssl=None,
        )

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
