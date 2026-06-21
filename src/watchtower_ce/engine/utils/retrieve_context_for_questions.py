import logging
from typing import Optional

from ..clients import ContextRetriever

logger = logging.getLogger(__name__)


def retrieve_context_for_questions(
    retriever: ContextRetriever, questions: list[str], retrieval_k: Optional[int] = None
) -> str:
    """
    Retrieve relevant compliance documentation for multiple questions.

    This method queries the vector store with each generated question and
    combines all retrieved contexts into a single comprehensive context string.
    Uses a set to automatically deduplicate retrieved document chunks.

    Args:
        questions (list[str]):
            List of compliance-related questions to search for.
        retrieval_k (Optional[int]):
            Optional override for the number of context chunks to retrieve per question.
            When provided, this value is passed directly to `ContextRetriever.context`.
            When `None` (the default), the retriever's own default retrieval configuration is used.

    Returns:
        str: Combined context from all retrievals, with double-newline separators
             between unique document chunks.
    """
    logger.info("Retrieving context for %s questions", len(questions))
    all_contexts = set()  # Using sets for automatic de-duplication of contexts

    for i, question in enumerate(questions, 1):
        logger.debug(
            'Retrieving context for question (%s/%s): "%s"',
            i,
            len(questions),
            question,
        )
        if retrieval_k:
            for context in retriever.context(question, retrieval_k):
                all_contexts.add(context.page_content)
        else:
            for context in retriever.context(question):
                all_contexts.add(context.page_content)

    combined_context = "\n\n--- Context chunks seperator ---\n\n".join(all_contexts)

    logger.info("Successfully retrieved context for %s questions", len(questions))
    return combined_context
