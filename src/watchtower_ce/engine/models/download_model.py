#!/usr/bin/env python3

from pathlib import Path

from huggingface_hub import snapshot_download
from yaspin import yaspin
from yaspin.spinners import Spinners


def download_model(
    model_name: str, model_path: str, required_files: list[str] | None = None
) -> None:
    """
    Note: if `required_files` is not specified, the function will always
    download the specified model.
    """

    # Construct path relative to this script's location
    script_dir = Path(__file__).parent
    model_path = f"base/{model_path}"
    local_dir = script_dir / model_path

    model_files_exist: bool = False

    if required_files:
        model_files_exist = all((local_dir / f).exists() for f in required_files)

    if not model_files_exist:
        with yaspin(Spinners.arc, text="[INFO] Downloading model..."):
            snapshot_download(
                repo_id=model_name, allow_patterns=required_files, local_dir=local_dir
            )
        print(f"[INFO] Model downloaded successfully to {local_dir}.")
    else:
        print(f"[INFO] Model {model_name} already downloaded to {local_dir}.")


if __name__ == "__main__":
    download_model(
        "bartowski/Ministral-8B-Instruct-2410-GGUF",
        "Ministral-8B-Instruct-2410-GGUF",
        ["Ministral-8B-Instruct-2410-Q6_K_L.gguf"],
    )
