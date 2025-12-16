#!/usr/bin/env python3

import warnings
from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from yaspin import yaspin
from yaspin.spinners import Spinners


class PDFToChroma:
    """
    A high-level utility for converting PDF files into Chroma vector database collections.

    This class automates the end-to-end pipeline of preparing a PDF for semantic search or
    Retrieval-Augmented Generation (RAG) workflows. It handles:
        1. Loading PDF pages into LangChain `Document` objects.
        2. Splitting text into manageable, overlapping chunks.
        3. Generating dense vector embeddings using a Hugging Face model.
        4. Persisting the vectors in a Chroma database collection.

    Workflow:
        1. Load the PDF into LangChain document objects.
        2. Split the text into overlapping chunks using a recursive character splitter.
        3. Create embeddings for each text chunk using a specified Hugging Face model.
        4. Store the resulting vectors in a Chroma database collection.

    Example:
        >>> builder = PDFToChroma(
        ...     pdf_path="data/pdfs/example.pdf",
        ...     persist_dir="data/chroma_db",
        ...     collection_name="example_collection"
        ... )
        >>> builder.build()
        [INFO] Successfully loaded 397 pages from example.pdf
        [INFO] Created 1303 text chunks
        [INFO] Collection "example_collection" successfully created and saved in /absolute/path/to/data/chroma_db
    """

    def __init__(
        self,
        pdf_path: str | Path,
        persist_dir: str | Path,
        collection_name: str | None = None,
        overwrite: bool = False,
        model_name: str = "sentence-transformers/all-MiniLM-L12-v2",
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> None:
        """
        Initializes the PDFToChroma builder.

        Args:
            pdf_path (str | Path):
                Path to the input PDF file to be processed.
            persist_dir (str | Path):
                Path to the directory where the Chroma database will be persisted.
            collection_name (str | None, optional):
                Name of the Chroma collection to create. Defaults to the PDF filename (without extension).
            overwrite (bool, optional):
                If `True`, any existing collection with the same name will be deleted and recreated.
                Defaults to `False`.
            model_name (str, optional):
                Name of the Hugging Face embedding model to use. Defaults to `"sentence-transformers/all-MiniLM-L12-v2"`.
            chunk_size (int, optional):
                Maximum number of characters per text chunk before embedding. Defaults to `800`.
            chunk_overlap (int, optional):
                Number of overlapping characters between consecutive chunks. Defaults to `100`.
        """
        self.pdf_path = Path(pdf_path)
        self.persist_dir = Path(persist_dir)
        self.collection_name = (
            collection_name or self.pdf_path.stem
        )  # default: filename
        self.overwrite = overwrite
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._embedding_model = None  # lazy initialization

    def _create_embeddings(self) -> HuggingFaceEmbeddings:
        """
        Initializes and return a Hugging Face embedding model.

        Returns:
            HuggingFaceEmbeddings: The initialized embedding model.
        """
        if self._embedding_model is None:
            with yaspin(Spinners.arc, text="[INFO] Loading embedding model..."):
                self._embedding_model = HuggingFaceEmbeddings(
                    model_name=self.model_name
                )
            print(f"[INFO] Successfully loaded embedding model {self.model_name}.")

        return self._embedding_model

    def _load_pdf(self) -> list[Document]:
        """
        Load the PDF file and return a list of LangChain `Document` objects.

        Each page of the PDF is converted into a single `Document` instance containing text and metadata.

        Returns:
            list[Document]: A list of `Document` objects, one per PDF page.
        """
        with yaspin(Spinners.arc, text="[INFO] Loading PDF..."):
            loader = PyPDFLoader(str(self.pdf_path))
            documents = loader.load()
        print(
            f"[INFO] Successfully loaded {len(documents)} pages from {self.pdf_path.name}."
        )

        return documents

    def _split_text(self, documents: list[Document]) -> list[Document]:
        """
        Split PDF text into smaller overlapping chunks suitable for embedding.

        This step helps prevent embedding models from being overloaded with large text blocks,
        while preserving some context between chunks.

        Args:
            documents (list[Document]): The loaded PDF pages as `Document` objects.

        Returns:
            list[Document]: The list of split text chunks.
        """
        with yaspin(Spinners.arc, text="[INFO] Splitting text into chunks..."):
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            texts = splitter.split_documents(documents)
        print(f"[INFO] Created {len(texts)} text chunks.")

        return texts

    def _handle_existing_collection(self) -> bool:
        """
        Check if the Chroma collection already exists and handle overwrite behavior.

        If the collection exists:
            - Deletes it if `overwrite=True`.
            - Issues a warning otherwise.

        Returns:
            bool: True if the collection previously existed, False otherwise.
        """
        client = chromadb.PersistentClient(path=str(self.persist_dir))
        exists: bool

        try:
            client.get_collection(self.collection_name)
            exists = True

            if self.overwrite:
                with yaspin(
                    Spinners.arc,
                    text=f'[INFO] Deleting existing collection "{self.collection_name}"...',
                ):
                    client.delete_collection(self.collection_name)
                print(
                    f'[INFO] Successfully deleted old collection "{self.collection_name}".'
                )
            else:
                warnings.warn(
                    f'[WARNING] Collection "{self.collection_name}" already exists in {self.persist_dir}. '
                    f"Set overwrite=True to overwrite it.",
                )

        except NotFoundError:
            if self.overwrite:
                print(f'[INFO] Collection "{self.collection_name}" does not exist.')
            exists = False

        return exists

    def build(self) -> None:
        """
        Run the full pipeline: load, split, embed, and store the PDF in Chroma.

        If `overwrite=False` and a collection with the same name already exists,
        the method will skip recreation and issue a warning instead.

        Returns:
                None
        """
        collection_exists: bool = self._handle_existing_collection()

        if self.overwrite or not collection_exists:
            documents = self._load_pdf()
            texts = self._split_text(documents)
            embedding_model = self._create_embeddings()

            with yaspin(
                Spinners.arc,
                text=f'[INFO] Creating collection "{self.collection_name}"...',
            ):
                Chroma.from_documents(
                    documents=texts,
                    embedding=embedding_model,
                    persist_directory=str(self.persist_dir),
                    collection_name=self.collection_name,
                )
            print(
                f'[INFO] Collection "{self.collection_name}" '
                f"successfully created and saved in {self.persist_dir.resolve()}."
            )
