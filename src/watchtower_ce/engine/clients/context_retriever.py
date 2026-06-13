import logging
import textwrap
from time import sleep
from typing import Generator

import httpx
from django.conf import settings
from httpx import ConnectError, TimeoutException
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

_chroma_client = httpx.Client(
    base_url=settings.CHROMA_SERVER_URL,
    timeout=httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=10.0),
    limits=httpx.Limits(max_keepalive_connections=10),
)


class ContextRetriever:
    """HTTP client wrapper around the context retrieval server."""

    def __init__(
        self,
        collection_name: str,
        retrieval_k: int = 4,
    ) -> None:
        """
        Initialize the ContextRetriever client.

        Args:
            collection_name (str):
                Name of the Chroma collection to query.
            retrieval_k (int):
                Number of most similar documents to retrieve for each query.
                Defaults to `4`.

        Raises:
            ConnectionError: If unable to connect to the retrieval server.
        """
        logger.debug(
            "Attempting to connect to retrieval server at %s", _chroma_client.base_url
        )
        for retries in range(5):
            try:
                response = _chroma_client.get("/health", timeout=5.0)
                response.raise_for_status()
                logger.debug(
                    "Successfully connected to retrieval server at %s",
                    _chroma_client.base_url,
                )
                break
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                logging.warning(f"Attempt {retries + 1} failed: {e}")
                logging.warning(
                    f"Waiting {5 * (2**retries)} seconds before retrying..."
                )
                sleep(5 * (2**retries))
        else:
            raise ConnectionError(
                "Failed to connect to retrieval server at %s after 5 attempts.",
                _chroma_client.base_url,
            )

        self.collection_name = collection_name
        self.retrieval_k = retrieval_k

    def context(
        self, query: str, retrieval_k: int | None = None
    ) -> Generator[Document, None, None]:
        """
        Retrieve the most semantically similar documents to a query as a generator.

        This method calls the retrieval server for similarity search and yields
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
            >>> retriever = ContextRetriever("PCI-DSS-v4.0.1")
            >>> for doc in retriever.context("Should I store CVV in my database?"):
            ...     print(doc.page_content)
        """
        current_k = retrieval_k if retrieval_k else self.retrieval_k

        if current_k < 1:
            raise ValueError("retrieval_k must be at least 1")

        logger.debug(
            'Retrieving top %s chunks from "%s" collection for query "%s"',
            current_k,
            self.collection_name,
            query,
        )

        try:
            response = _chroma_client.post(
                "/retrieve",
                json={
                    "query": query,
                    "collection_name": self.collection_name,
                    "k": current_k,
                },
            )
            response.raise_for_status()
            data = response.json()

            logger.debug(
                'Successfully retrieved top %s chunks from "%s" collection for query "%s"',
                len(data["documents"]),
                self.collection_name,
                query,
            )

            # Yield documents from response
            for doc_data in data["documents"]:
                yield Document(
                    page_content=doc_data["page_content"],
                    metadata=doc_data.get("metadata", {}),
                )

        except httpx.HTTPError as e:
            logger.error(
                'HTTP error retrieving context for query "%s" from collection "%s": %s',
                query,
                self.collection_name,
                e,
            )
            raise
        except Exception as e:
            logger.error(
                'Failed to retrieve context for query "%s" from collection "%s": %s',
                query,
                self.collection_name,
                e,
            )
            raise

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
            >>> retriever = ContextRetriever("PCI-DSS-v4.0.1", 3)
            >>> context = retriever.retrieve("encryption requirements")
            >>> print(context)  # Prints all retrieved documents as one string
        """
        return textwrap.dedent(
            "\n\n".join([doc.page_content for doc in self.context(query, retrieval_k)])
        )

    def health(self) -> dict:
        """
        Check the health of the retrieval server.

        Returns:
            dict: A dictionary containing the health status, embedding model status, and number of available collections.
        """
        try:
            response = _chroma_client.get(
                "/health",
                timeout=5.0,
            )

            # Both 200 and 503 return the same structure from server
            if response.status_code in [
                httpx.codes.OK,
                httpx.codes.SERVICE_UNAVAILABLE,
            ]:
                return {
                    "status": response.json()["status"],
                    "details": {
                        k: v for k, v in response.json().items() if k != "status"
                    },
                }
            else:
                # Any other status code (500, 404, etc.)
                return {
                    "status": "error",
                    "details": {
                        "error": f"HTTP {response.status_code}: {response.text}",
                    },
                }

        except ConnectError:
            return {
                "status": "unavailable",
                "details": {
                    "error": f"Cannot connect to server at {_chroma_client.base_url}",
                },
            }
        except TimeoutException:
            return {
                "status": "unavailable",
                "details": {
                    "error": f"Connection to {_chroma_client.base_url} timed out",
                },
            }
        except Exception as e:
            return {
                "status": "error",
                "details": {
                    "error": f"Unexpected error: {str(e)}",
                },
            }
