import click

from .download import download
from .server import server
from .test import test


@click.group()
@click.help_option("-h", "--help")
def main():
    pass


main.add_command(download)
main.add_command(server)
main.add_command(test)
