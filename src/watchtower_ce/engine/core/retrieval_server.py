# TODO: Refactor this into a separate module/repository

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import BaseModel
from transformers.utils import logging as transformers_logging

logger = logging.getLogger(__name__)
transformers_logging.disable_progress_bar()

# Global instances; loaded once at server startup
_EMBEDDING_MODEL: Optional[HuggingFaceEmbeddings] = None
_RETRIEVERS: dict[str, Chroma] = {}  # collection_name : Chroma retriever


class RetrievalRequest(BaseModel):
    """Request model for similarity search."""

    query: str
    collection_name: str
    k: int = 4


class RetrievedDocument(BaseModel):
    """Retrieved document with content and metadata."""

    page_content: str
    metadata: dict


class RetrievalResponse(BaseModel):
    """Response model for similarity search."""

    documents: list[RetrievedDocument]
    query: str
    collection_name: str
    k: int


def initialize_server(
    chroma_dir: Path | str,
    embedding_model: Path | str = "sentence-transformers/all-MiniLM-L12-v2",
) -> None:
    """
    Initialize the retrieval server with embedding model and collections.

    Should be called once at server startup before handling requests.

    Args:
        chroma_dir: Path to Chroma database persistence directory
        embedding_model: HuggingFace embedding model identifier or path.
            If not a local path, will download from HuggingFace Hub.
    """
    global _EMBEDDING_MODEL, _RETRIEVERS

    logger.info("Loading embedding model...")

    # Check if the embedding model is available locally, and download if not
    if not Path(embedding_model).is_dir():
        logger.warning(
            "Embedding model not found locally. Downloading from HuggingFace Hub: %s",
            embedding_model,
        )

    _EMBEDDING_MODEL = HuggingFaceEmbeddings(
        model_name=str(embedding_model),
        model_kwargs={"device": "cpu"},
    )

    logger.info("Successfully loaded embedding model")

    # Auto-discover and load all collections from Chroma directory
    import chromadb

    chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
    collections = chroma_client.list_collections()

    logger.info("Found %d collections in Chroma database", len(collections))

    for collection_info in collections:
        collection_name = collection_info.name
        logger.debug("Loading collection: %s", collection_name)

        try:
            retriever = Chroma(
                persist_directory=str(chroma_dir),
                collection_name=collection_name,
                embedding_function=_EMBEDDING_MODEL,
            )
            _RETRIEVERS[collection_name] = retriever
            logger.debug("Successfully loaded collection: %s", collection_name)
        except Exception as e:
            logger.error("Failed to load collection %s: %s", collection_name, e)

    if len(_RETRIEVERS) < len(collections):
        logger.warning(
            "Retrieval server initialized with %d/%d collections",
            len(_RETRIEVERS),
            len(collections),
        )
    else:
        logger.info(
            "Retrieval server initialized with %d/%d collections",
            len(_RETRIEVERS),
            len(collections),
        )


app = FastAPI(
    title="Watchtower Retrieval Server",
    description="Semantic similarity search server for compliance documents",
    version="1.0.0",  # probably gonna be in this version perpetually lol
)


@app.post("/retrieve", response_model=RetrievalResponse)
async def retrieve(request: RetrievalRequest) -> RetrievalResponse:
    """
    Retrieve semantically similar documents from a collection.

    Args:
        request: RetrievalRequest with query, collection_name, and k (top results)

    Returns:
        RetrievalResponse with retrieved documents

    Raises:
        HTTPException: If collection not found or retrieval fails
    """
    if request.collection_name not in _RETRIEVERS:
        available = list(_RETRIEVERS.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{request.collection_name}' not found. Available collections: {available}",
        )

    try:
        retriever = _RETRIEVERS[request.collection_name]
        results = retriever.similarity_search(request.query, k=request.k)

        documents = [
            RetrievedDocument(
                page_content=doc.page_content, metadata=doc.metadata or {}
            )
            for doc in results
        ]

        logger.debug(
            'Retrieved %d documents for query "%s" from collection "%s"',
            len(documents),
            request.query,
            request.collection_name,
        )

        return RetrievalResponse(
            documents=documents,
            query=request.query,
            collection_name=request.collection_name,
            k=request.k,
        )

    except Exception as e:
        logger.error(
            'Retrieval failed for query "%s" from collection "%s": %s',
            request.query,
            request.collection_name,
            e,
        )
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")


@app.get("/health")
async def health() -> dict:
    """
    Health check endpoint.

    Returns:
        A dictionary containing the health status of the server.

    Example:
        {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": "2025-09-28T12:00:00",
            "components": {
                "embedding_model": "up",
                "collections": 3,
                "collections_ready": 3,
            },
        }
    """
    response = {
        "status": "healthy" if _EMBEDDING_MODEL and _RETRIEVERS else "degraded",
        "version": app.version,
        "timestamp": datetime.now().isoformat(),
        "components": {
            "embedding_model": "up" if _EMBEDDING_MODEL else "down",
            "collections_count": len(_RETRIEVERS),
            "collections_ready": sum(1 for r in _RETRIEVERS.values() if r._collection),
            "collections": {},
        },
    }

    # Check each collection
    for name, retriever in _RETRIEVERS.items():
        try:
            retriever._collection.count()
            response["components"]["collections"][name] = "ok"
        except Exception:
            response["components"]["collections"][name] = "error"
            response["status"] = "degraded"

    if response["status"] != "healthy":
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=response)
    return response


@app.get("/collections")
async def list_collections() -> dict:
    """
    List all available collections.

    Returns:
        Dictionary with collection names and their metadata
    """
    result = {}
    for name, retriever in _RETRIEVERS.items():
        try:
            # Get collection stats
            collection = retriever._collection
            result[name] = {
                "count": collection.count()
                if hasattr(collection, "count")
                else "unknown",
                "metadata": collection.metadata
                if hasattr(collection, "metadata")
                else {},
            }
        except Exception as e:
            logger.error("Error getting stats for collection %s: %s", name, e)
            result[name] = {"error": str(e)}

    return {"collections": result}
