from pathlib import Path

import click
from huggingface_hub import snapshot_download


@click.command(
    "embedding",
    short_help="Download an embeddings model",
    help="Download an embeddings model from HuggingFace.",
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
    help="Model directory on disk. Can be relative to the current working directory or absolute.",
    default="",
)
def embedding(name: str, output_dir: str) -> None:
    """
    Downloads a model to a local directory from HuggingFace Hub for offline use.

    Args:
        name (str):
            The model identifier on HuggingFace Hub.
        output_dir (str):
            The directory to save the model to. Can be relative or absolute.
            Defaults to ./embeddings/<model_name> in the current working directory.
    """
    if not output_dir:
        # Default to an 'embeddings' directory in the current working directory
        absolute_path = Path.cwd() / "embeddings" / name
    else:
        absolute_path = Path(output_dir).resolve()

    # Check if directory already exists and is not empty
    if absolute_path.exists() and any(absolute_path.iterdir()):
        print(f"Directory '{absolute_path}' already exists and is not empty.")
        return

    # Ensure parent directory exists
    absolute_path.mkdir(parents=True, exist_ok=True)

    print(f"Downloading embedding model '{name}' via huggingface_hub...")
    snapshot_download(repo_id=name, local_dir=absolute_path)
    print(f"Model downloaded successfully to {absolute_path}")
