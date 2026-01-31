from pathlib import Path

import click
from huggingface_hub import snapshot_download


@click.command(
    "base",
    short_help="Downloads a base GGUF LLM model.",
    help="Downloads a base GGUF LLM model from HuggingFace.",
)
@click.help_option("-h", "--help")
@click.option(
    "-n",
    "--name",
    type=str,
    help="Model name/identifier on HuggingFace Hub.",
    default="bartowski/Ministral-8B-Instruct-2410-GGUF",
)
@click.option(
    "-o",
    "--output_dir",
    type=str,
    help="Model directory on disk. Can be relative (to script directory) or absolute.",
    default="",
)
@click.option(
    "-r",
    "--required_files",
    type=str,
    help="Required files to download. If not specified, all files will be downloaded.",
    default=[],
    multiple=True,
)
def base(name: str, output_dir: str, required_files: tuple[str, ...]) -> None:
    """
    Downloads a base GGUF LLM model from HuggingFace.

    Args:
        name (str):
            Model name/identifier on HuggingFace Hub.
        path (str):
            Model path on disk. Can be relative (to script directory) or absolute.
        required_files (tuple[str, ...]):
            Required files to download. If not specified, all files will be downloaded.

    Note:
        If `required_files` is not specified, the function will always
        download the entire model.
    """
    if not output_dir:
        # Default to a 'base' directory relative to this script
        current_dir = Path(__file__).parent
        absolute_path = current_dir / "base" / name
    else:
        path_obj = Path(output_dir)

        # If path is relative, make it relative to the script's directory
        # If path is absolute, this will just use the absolute path
        if not path_obj.is_absolute():
            absolute_path = Path(__file__).parent / path_obj
        else:
            absolute_path = path_obj

    # Ensure parent directory exists
    absolute_path.mkdir(parents=True, exist_ok=True)

    patterns = list(required_files) if required_files else None

    if patterns:
        model_files_exist = all((absolute_path / f).exists() for f in patterns)
    else:
        model_files_exist = False  # Always download if no specific files specified

    if not model_files_exist:
        print("Downloading model...")
        snapshot_download(
            repo_id=name,
            local_dir=absolute_path,
            allow_patterns=patterns,
        )
        print(f"Model downloaded successfully to {absolute_path}.")
    else:
        print(f"Model {name} already downloaded to {absolute_path}.")
