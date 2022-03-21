"""all commands here"""
import click

from .serv import run_client
from .serv import run_server


@click.group()
def cli():
    """all clicks here"""


cli.add_command(run_client)
cli.add_command(run_server)
