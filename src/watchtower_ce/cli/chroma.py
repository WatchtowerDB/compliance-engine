import logging
from pathlib import Path

import click
import uvicorn
from django.conf import settings
from uvicorn.config import LOGGING_CONFIG

logger = logging.getLogger(__name__)
# Changing the very unforunate name of the uvicorn logger
uvicorn_logger = logging.getLogger("uvicorn.error")
uvicorn_logger.name = "uvicorn"

LOGGING_CONFIG["formatters"]["default"]["fmt"] = (
    "[%(asctime)s: %(name)s] %(levelprefix)s %(message)s"
)
logging.basicConfig(
    level=logging.WARNING,
    format="[%(asctime)s: %(name)s] %(levelname)s %(message)s",
)


@click.command(
    "chroma",
    short_help="Start Chroma retrieval server",
    help="Start Chroma retrieval server for semantic document retrieval",
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
    "-P",
    "--port",
    type=int,
    help="Listen port",
    default=7777,
)
@click.option(
    "-d",
    "--chroma-dir",
    type=click.Path(exists=True),
    help="Path to Chroma database directory",
    default=None,
)
@click.option(
    "-m",
    "--embedding-model",
    type=str,
    help="HuggingFace embedding model identifier or path",
    default=None,
)
@click.option(
    "-l",
    "--log-level",
    type=str,
    help="Log level (debug, info, warning, error, critical)",
    default="info",
)
def chroma(
    host: str,
    port: int,
    chroma_dir: str | None,
    embedding_model: str | None,
    log_level: str,
) -> None:
    """Start the Chroma retrieval server."""
    from ..engine.core.retrieval_server import app, initialize_server

    logging.getLogger("watchtower_ce").setLevel(getattr(logging, log_level.upper()))
    # Initialize Django if not already initialized
    if not settings.configured:
        import django

        django.setup()

    # Use provided values or fall back to settings
    chroma_path = chroma_dir or settings.CHROMA_DIR
    model_name = embedding_model or settings.CHROMA_EMBEDDING_MODEL_DIR

    logger.info("Starting Chroma retrieval server on %s:%d", host, port)
    logger.info("Using Chroma database at: %s", chroma_path)
    logger.info("Using embedding model: %s", model_name)

    # Initialize retrieval server
    initialize_server(
        chroma_dir=Path(chroma_path),
        embedding_model=model_name,
    )

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
    )
