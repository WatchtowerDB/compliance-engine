import click

from .download_model import download_model
from .server import server
from .test import test


@click.group()
@click.help_option("-h", "--help")
def main():
    pass


main.add_command(download_model)
main.add_command(server)
main.add_command(test)
