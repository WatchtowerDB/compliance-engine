from pathlib import Path

import click
from sentence_transformers import SentenceTransformer


@click.command(
    "embedding",
    short_help="Downloads a Sentence Transformer embeddings model.",
    help="Downloads a Sentence Transformer embeddings model from HuggingFace.",
)
@click.help_option("-h", "--help")
@click.option(
    "-n",
    "--name",
    type=str,
    help="Model name/identifier on HuggingFace Hub.",
    default="sentence-transformers/all-MiniLM-L12-v2",
)
@click.option(
    "-o",
    "--output_dir",
    type=str,
    help="Model directory on disk. Can be relative (to script directory) or absolute.",
    default="",
)
def embedding(
    name: str,
    output_dir: str,
) -> None:
    """
    Downloads a Sentence Transformer model to a local directory for offline use.

    Args:
        name (str):
            The model identifier on HuggingFace Hub.
        output_dir (str):
            The directory to save the model to. Can be relative or absolute.
            Defaults to ./embedding/<model_name> relative to this script.
    """
    if not output_dir:
        # Default to a 'embedding' directory relative to this script
        current_dir = Path(__file__).parent
        absolute_path = current_dir / "embedding" / name
    else:
        path_obj = Path(output_dir)

        # If path is relative, make it relative to the script's directorym
        # If path is absolute, this will just use the absolute path
        if not path_obj.is_absolute():
            absolute_path = Path(__file__).parent / path_obj
        else:
            absolute_path = path_obj

    # Ensure parent directory exists
    absolute_path.mkdir(parents=True, exist_ok=True)

    print(f"Downloading embedding model '{name}'...")
    model = SentenceTransformer(name)

    print(f"Saving model to '{absolute_path}'...")
    model.save_pretrained(str(absolute_path))
    print(f"Model saved successfully to {absolute_path}")
