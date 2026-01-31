from pathlib import Path

from sentence_transformers import SentenceTransformer


def download_embedding_model(
    model_name: str = "sentence-transformers/all-MiniLM-L12-v2",
    output_dir: Path | str | None = None,
) -> None:
    """
    Downloads a Sentence Transformer model to a local directory for offline use.

    Args:
        model_name (str):
            The model identifier on HuggingFace Hub.
        output_dir (Path | str | None):
            The directory to save the model to.
            Defaults to ./embeddings/<model_name> relative to this script.
    """
    if output_dir is None:
        # Default to a 'embeddings' directory relative to this script
        current_dir = Path(__file__).parent
        output_dir = current_dir / "embeddings" / model_name

    output_path = Path(output_dir)

    print(f"Downloading embedding model '{model_name}'...")
    model = SentenceTransformer(model_name)

    print(f"Saving model to '{output_path}'...")
    model.save_pretrained(str(output_path))
    print(f"Model saved successfully to {output_path}")


if __name__ == "__main__":
    download_embedding_model(
        model_name="sentence-transformers/all-MiniLM-L12-v2",
        output_dir="models/embeddings/all-MiniLM-L12-v2",
    )
