import logging
import textwrap
from pathlib import Path
from typing import Generator

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


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
        embedding_model: Path | str = "sentence-transformers/all-MiniLM-L12-v2",
        retrieval_k: int = 4,
    ) -> None:
        """
        Initialize the ContextRetriever with a Chroma vector store and embedding model.

        Args:
            chroma_dir (Path | str):
                Path to the directory containing the persisted Chroma database.
            collection_name (str):
                Name of the collection within the Chroma database to use.
            embedding_model (Path | str):
                HuggingFace model identifier or local path for text embeddings.
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

        logger.info('Loading embedding model "%s"', embedding_model)
        self._embedding_model = HuggingFaceEmbeddings(
            model_name=str(embedding_model), model_kwargs={"device": "cpu"}
        )
        logger.info('Successfully loaded embedding model "%s"', embedding_model)

        logger.info('Initializing Chroma retriever for "%s"', self.collection_name)
        self._retriever = Chroma(
            persist_directory=str(self.chroma_dir),
            collection_name=self.collection_name,
            embedding_function=self._embedding_model,
        )
        logger.info(
            'Successfully initialized Chroma retriever for "%s"', self.collection_name
        )

    def context(
        self, query: str, retrieval_k: int | None = None
    ) -> Generator[Document, None, None]:
        """
        Retrieve the most semantically similar documents to a query as a generator.

        This method performs a similarity search in the vector store and yields
        documents one at a time, allowing for memory-efficient processing of results.
        Each document contains the retrieved text content along with metadata.

        Args:
            query (str):
                The search query string to find similar documents for.
            retrieval_k (int | None):
                Number of top similar documents to retrieve per query.
                Defaults to the class `retrieval_k` if not specified.

        Yields:
            Document: LangChain Document objects containing `page_content` (`str`) and
                      `metadata` (`dict`). Documents are yielded in order of decreasing similarity.

        Example:
            >>> retriever = ContextRetriever("./chroma_db", "my_collection")
            >>> for doc in retriever.context("What is encryption?"):
            ...     print(doc.page_content)
        """
        current_k = retrieval_k if retrieval_k else self.retrieval_k

        logger.debug(
            'Retrieving top %s chunks from "%s" collection for query "%s"',
            current_k,
            self.collection_name,
            query,
        )
        results = self._retriever.similarity_search(query, k=current_k)
        logger.debug(
            'Successfully retrieved top %s chunks from "%s" collection for query "%s"',
            current_k,
            self.collection_name,
            query,
        )

        for doc in results:
            yield doc

    def retrieve(self, query: str, retrieval_k: int | None = None) -> str:
        """
        Retrieve the most similar documents and return them as a concatenated string.

        This is a convenience method that wraps the `context()` generator, collecting
        all retrieved documents and joining their content with double newlines for
        readability. Useful for when you need all context as a single string.

        Args:
            query (str):
                The search query string to find similar documents for.
            retrieval_k (int | None):
                Number of top similar documents to retrieve per query.
                Defaults to the class `retrieval_k` if not specified.

        Returns:
            str: A single string containing all retrieved document contents,
                 separated by double newlines. The string is dedented to remove
                 common leading whitespace.

        Example:
            >>> retriever = ContextRetriever("./chroma_db", "my_collection")
            >>> context = retriever.retrieve("encryption requirements")
            >>> print(context)  # Prints all retrieved documents as one string
        """
        return textwrap.dedent(
            "\n\n".join([doc.page_content for doc in self.context(query, retrieval_k)])
        )
