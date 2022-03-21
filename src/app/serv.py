"""server / client services"""
import asyncio
import logging

import click

from . import cfg
from .client_server import ClientRemoteProtocol
from .client_server import ClientServerProtocol
from .proxy_server import ProxyServerProtocol

LOGGER = logging.getLogger(__name__)


@click.command()
def run_client():
    """run client"""

    async def handle_client(reader, writer):
        local = ClientServerProtocol(reader, writer)
        remote = await ClientRemoteProtocol.create_connection(
            cfg.proxy_server['host_public'], cfg.proxy_server['port'])
        return asyncio.ensure_future(remote.exchange_data(local))

    async def service(h: str = cfg.proxy_client['host'],
                      p: int = cfg.proxy_client['port']):
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

    async def service(h: str = cfg.proxy_server['host'],
                      p: int = cfg.proxy_server['port']):
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
