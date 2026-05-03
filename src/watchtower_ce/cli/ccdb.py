from pathlib import Path

import click

from ..engine.utils.pdf_to_chroma import PDFToChroma


@click.command(
    "ccdb",
    short_help="Create a Chroma DB from PDF",
    help="Create a Chroma DB from a given PDF file.",
)
@click.help_option("-h", "--help")
@click.option(
    "-p",
    "--pdf_path",
    type=str,
    help="Path to the input PDF file to be processed. Can be relative to the current working directory or absolute.",
)
@click.option(
    "-d",
    "--persist_dir",
    type=str,
    help="Path to the directory where the Chroma database is/will be persisted. Can be relative to the current working directory or absolute.",
    default=None,
)
@click.option(
    "-c",
    "--collection_name",
    type=str,
    help="Name of the Chroma collection to create. Defaults to the PDF filename (without extension).",
    default=None,
)
@click.option(
    "-o",
    "--overwrite",
    is_flag=True,
    help="If set, any existing collection with the same name will be deleted and recreated.",
)
@click.option(
    "-m",
    "--model_name",
    type=str,
    help='HuggingFace model identifier or local path (relative or absolute) for text embeddings. Defaults to "sentence-transformers/all-MiniLM-L12-v2", a lightweight but effective sentence embedding model.',
    default="sentence-transformers/all-MiniLM-L12-v2",
)
@click.option(
    "-s",
    "--seperators",
    type=str,
    help="If set, the chunks will be split based on these separators. If not, chunk_size and chunk_overlap will be used.\n\n"
    'Pro-tip: use "\\f" (form feed) to split by PDF page. Not guaranteed to work with all PDFs, but can be a good option for well-structured documents.',
    default=[],
    multiple=True,
)
@click.option(
    "-S",
    "--chunk_size",
    type=int,
    help="Maximum number of characters per text chunk before embedding. Defaults to 800.",
)
@click.option(
    "-O",
    "--chunk_overlap",
    type=int,
    help="Number of overlapping characters between consecutive chunks. Defaults to 100.",
)
def ccdb(
    pdf_path: str,
    persist_dir: str,
    collection_name: str,
    overwrite: bool,
    model_name: str,
    seperators: tuple[str, ...],
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    """
    Creates a Chroma DB collection from a PDF file.

    This command processes a PDF file, splits it into chunks, generates embeddings
    using a specified model, and persists them into a Chroma vector database.
    It's simply a CLI wrapper around the PDFToChroma class.

    Args:
        pdf_path (str):
            Path to the input PDF file. Can be relative or absolute.
        persist_dir (str):
            Directory where the Chroma database will be saved.
            Defaults to ./data/chroma_db in the current working directory.
        collection_name (str):
            Name of the collection. Defaults to the PDF filename.
        overwrite (bool):
            If True, deletes and recreates the collection if it already exists.
        model_name (str):
            HuggingFace model identifier or local path to the embedding model.
        seperators (tuple[str, ...]):
            List of separators for splitting text.
        chunk_size (int):
            Maximum characters per chunk. Defaults to 800.
        chunk_overlap (int):
            Overlap between chunks. Defaults to 100.
    """
    if not pdf_path:
        raise ValueError("PDF path is required.")

    absolute_pdf_path = Path(pdf_path).resolve()

    if not persist_dir:
        absolute_persist_dir = Path.cwd() / "data" / "chroma_db"
    else:
        absolute_persist_dir = Path(persist_dir).resolve()

    # Resolve model_name: can be a local path (relative/absolute) or a HuggingFace ID.
    potential_local_path = Path(model_name).resolve()

    # If the resolved path exists as a directory, use it. Otherwise, assume it's a HuggingFace ID.
    if potential_local_path.is_dir():
        final_model_name = potential_local_path
    else:
        final_model_name = model_name

    # Handle defaults for optional arguments that might be None
    separators_list = list(seperators) if seperators else None
    chunk_size = chunk_size if chunk_size is not None else 800
    chunk_overlap = chunk_overlap if chunk_overlap is not None else 100

    builder = PDFToChroma(
        pdf_path=absolute_pdf_path,
        persist_dir=absolute_persist_dir,
        collection_name=collection_name,
        overwrite=overwrite,
        model_name=final_model_name,
        separators=separators_list,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    builder.build()
