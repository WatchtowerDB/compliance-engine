from pathlib import Path

import click


@click.command(
    "download_model",
    short_help="Download a base GGUF LLM model",
    help="Download a base GGUF LLM model from HuggingFace.",
)
@click.help_option("-h", "--help")
@click.option(
    "-n",
    "--name",
    type=str,
    help="Model name/identifier on HuggingFace Hub.",
    default="unsloth/gemma-4-E4B-it-GGUF",
)
@click.option(
    "-o",
    "--output_dir",
    type=str,
    help="Model directory on disk. Can be relative to the current working directory or absolute.",
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
def download_model(name: str, output_dir: str, required_files: tuple[str, ...]) -> None:
    """
    Downloads a base GGUF LLM model from HuggingFace.

    Args:
        name (str):
            Model name/identifier on HuggingFace Hub.
        output_dir (str):
            The directory to save the model to. Can be relative or absolute.
            Defaults to ./base/<model_name> in the current working directory.
        required_files (tuple[str, ...]):
            Required files to download. If not specified, all files will be downloaded.

    Note:
        If `required_files` is not specified, the function will always
        download the entire model.
    """
    from huggingface_hub import (
        snapshot_download,  # lazy import to make it an optional dependency
    )

    if not output_dir:
        # Default to a 'base' directory in the current working directory
        absolute_path = Path.cwd() / "base" / name
    else:
        absolute_path = Path(output_dir).resolve()

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
