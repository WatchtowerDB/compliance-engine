import click

from .download import download
from .server import server


@click.group()
@click.help_option("--help", "-h")
def main():
    pass


main.add_command(server)
main.add_command(download)
