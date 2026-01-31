import click

from .base import base
from .embedding import embedding


@click.group(help="Download a model")
def download():
    pass


download.add_command(base)
download.add_command(embedding)
