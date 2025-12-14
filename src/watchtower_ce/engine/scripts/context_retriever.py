#!/usr/bin/env python3

import textwrap
from pathlib import Path
from typing import Generator

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from yaspin import yaspin
from yaspin.spinners import Spinners


class ContextRetriever:
    """
    Handles retrieval of relevant context from a vector store using semantic search.

    This class provides an interface to a Chroma vector database, enabling semantic
    similarity search over embedded documents. It uses HuggingFace embedding models
    to convert queries into vector representations for comparison with stored documents.

    Attributes:
            chroma_dir (Path):
                    Directory path where the Chroma database is persisted.
            collection_name (str):
                    Name of the Chroma collection to query.
            retrieval_k (int):
                    Number of top similar documents to retrieve per query.
            _embedding_model (HuggingFaceEmbeddings):
                    The embedding model used for vectorization.
            _retriever (Chroma):
                    The Chroma vector store instance.
    """

    def __init__(
        self,
        chroma_dir: Path | str,
        collection_name: str,
        embedding_model: str = "sentence-transformers/all-MiniLM-L12-v2",
        retrieval_k: int = 4,
    ) -> None:
        """
        Initialize the ContextRetriever with a Chroma vector store and embedding model.

        Args:
                chroma_dir (Path | str):
                        Path to the directory containing the persisted Chroma database.
                collection_name (str):
                        Name of the collection within the Chroma database to use.
                embedding_model (str):
                        HuggingFace model identifier for text embeddings.
                        Defaults to `"sentence-transformers/all-MiniLM-L12-v2"`, a lightweight
                        but effective sentence embedding model.
                retrieval_k (int):
                        Number of most similar documents to retrieve for each query.
                        Defaults to `4`.

        Raises:
                ValueError: If the Chroma directory or collection doesn't exist.
                OSError: If there are file system access issues.
        """
        self.chroma_dir = Path(chroma_dir)
        self.collection_name = collection_name
        self.retrieval_k = retrieval_k
        self._embedding_model: HuggingFaceEmbeddings
        self._retriever: Chroma

        with yaspin(Spinners.arc, text="[INFO] Loading embedding model..."):
            self._embedding_model = HuggingFaceEmbeddings(model_name=embedding_model)
        print(f'[INFO] Successfully loaded embedding model "{embedding_model}".')

        with yaspin(Spinners.arc, text="[INFO] Initializing Chroma retriever..."):
            self._retriever = Chroma(
                persist_directory=str(self.chroma_dir),
                collection_name=self.collection_name,
                embedding_function=self._embedding_model,
            )
        print("[INFO] Successfully initialized Chroma retriever.")

    def context(self, query: str) -> Generator[Document, None, None]:
        """
        Retrieve the most semantically similar documents to a query as a generator.

        This method performs a similarity search in the vector store and yields
        documents one at a time, allowing for memory-efficient processing of results.
        Each document contains the retrieved text content along with metadata.

        Args:
                query (str):
                        The search query string to find similar documents for.

        Yields:
                Document: LangChain Document objects containing `page_content` (`str`) and
                        `metadata` (`dict`). Documents are yielded in order of decreasing similarity.

        Example:
                >>> retriever = ContextRetriever("./chroma_db", "my_collection")
                >>> for doc in retriever.context("What is encryption?"):
                ... 	print(doc.page_content)
        """
        with yaspin(
            Spinners.arc, text=f"[INFO] Retrieving top {self.retrieval_k} chunks..."
        ):
            results = self._retriever.similarity_search(query, k=self.retrieval_k)
        print(f"[INFO] Retrieved context from {self.collection_name} collection.")

        for doc in results:
            yield doc

    def retrieve(self, query: str) -> str:
        """
        Retrieve the most similar documents and return them as a concatenated string.

        This is a convenience method that wraps the `context()` generator, collecting
        all retrieved documents and joining their content with double newlines for
        readability. Useful for when you need all context as a single string.

        Args:
                query (str):
                        The search query string to find similar documents for.

        Returns:
                str: A single string containing all retrieved document contents,
                        separated by double newlines. The string is dedented to remove
                        common leading whitespace.

        Example:
                >>> retriever = ContextRetriever("./chroma_db", "my_collection")
                >>> context = retriever.retrieve("encryption requirements")
                >>> print(context)	# Prints all retrieved documents as one string
        """
        return textwrap.dedent(
            "\n\n".join([doc.page_content for doc in self.context(query)])
        )
