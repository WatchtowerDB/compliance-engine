import click

from .base import base
from .embedding import embedding


@click.group(help="Download a model")
@click.help_option("--help", "-h")
def download():
    pass


download.add_command(base)
download.add_command(embedding)
