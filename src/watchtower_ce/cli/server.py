import click
import uvicorn

from ..asgi import application


@click.command(
    "server",
    short_help="Start HTTP server",
    help="Start HTTP server for Watchtower Compliance Engine API",
)
@click.help_option("-h", "--help")
@click.option(
    "-H",
    "--host",
    type=str,
    help="Listen address",
    default="0.0.0.0",
)
@click.option(
    "-p",
    "--port",
    type=int,
    help="Listen port",
    default=8000,
)
def server(host: str, port: int) -> None:
    uvicorn.run(
        application,
        host=host,
        port=port,
        log_level="info",
    )
