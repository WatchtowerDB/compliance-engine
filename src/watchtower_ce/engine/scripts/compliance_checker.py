import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator
from warnings import deprecated

from llama_cpp import CreateCompletionStreamResponse

from .context_retriever import ContextRetriever
from .llm_inference import LLMInference

logger = logging.getLogger(__name__)


class ComplianceChecker(ABC):
    """
    Abstract base class for RAG-powered compliance analysis systems using assertions.

    This class provides a framework for building compliance checkers that use
    Retrieval Augmented Generation (RAG) to analyze schemas, configurations, or
    other artifacts against specific compliance standards (PCI-DSS, HIPAA, GDPR, etc.).

    The workflow:
    1. Generate SQL assertions to verify compliance (executed externally)
    2. Analyze failed assertions using retrieved context
    3. Provide specific remediation recommendations

    Subclasses must implement standard-specific prompt engineering and analysis logic.

    Attributes:
        context_retriever (ContextRetriever):
            Vector store interface for document retrieval.
        llm (LLMInference):
            Language model interface for generation tasks.
    """

    def __init__(
        self,
        model_path: Path | str,
        chroma_dir: Path | str,
        collection_name: str,
        embedding_model: str = "sentence-transformers/all-MiniLM-L12-v2",
        retrieval_k: int = 4,
        context_window: int = 4096,
        n_gpu_layers: int = -1,
        prompt_template: str = "[INST] {prompt} [/INST]",
        stop: str | list[str] | None = ["[INST]", "[/INST]"],
    ) -> None:
        """
        Initialize the compliance checker with RAG components.

        Args:
            model_path (Path | str):
                Path to the GGUF model file for LLM inference.
            chroma_dir (Path | str):
                Directory containing the Chroma vector database.
            collection_name (str):
                Name of the Chroma collection with compliance documents.
            embedding_model (str):
                HuggingFace model for text embeddings.
                Defaults to `"sentence-transformers/all-MiniLM-L12-v2"`.
            retrieval_k (int):
                Number of similar documents to retrieve per query. Defaults to `4`.
            context_window (int):
                Maximum context length for the LLM in tokens. Defaults to `4096`.
            n_gpu_layers (int):
                GPU layers to offload. `-1` for all, `0` for CPU only. Defaults to `-1`.
            prompt_template (str):
                Template for formatting LLM prompts. Should include `{prompt}`
                placeholder. Defaults to Mistral format: `"[INST] {prompt} [/INST]"`.
            stop (str | list[str] | None):
                Stop sequences for generation. Defaults to `["[INST]", "[/INST]"]`.
        """
        self.context_retriever = ContextRetriever(
            chroma_dir=chroma_dir,
            collection_name=collection_name,
            embedding_model=embedding_model,
            retrieval_k=retrieval_k,
        )
        self.llm = LLMInference(
            model_path=model_path,
            context_window=context_window,
            n_gpu_layers=n_gpu_layers,
            prompt_template=prompt_template,
            stop=stop,
        )

    @abstractmethod
    def _build_schema_questions_prompt(self, schema: str) -> str:
        """
        Construct a prompt for generating compliance-specific questions for an SQL schema.

        This method should create a prompt that instructs the LLM to analyze the
        input schema and generate targeted questions that will be
        used to retrieve relevant compliance documentation.

        Args:
            schema (str):
                The SQL schema to analyze.

        Returns:
            str: A prompt instructing the LLM to generate compliance questions.

        Note:
            Subclasses should instruct the model to return a Python list of strings.
        """
        pass

    @abstractmethod
    def _build_assertion_questions_prompt(self, assertion: str) -> str:
        """
        Construct a prompt for generating compliance-specific questions for an SQL assertion.

        This method should create a prompt that instructs the LLM to analyze the
        input assertion and generate targeted questions that will be
        used to retrieve relevant compliance documentation.

        Args:
            assertion (str):
                An sql assertion to analyze.

        Returns:
            str: A prompt instructing the LLM to generate compliance questions.

        Note:
            Subclasses should instruct the model to return a Python list of strings.
        """
        pass

    @abstractmethod
    def _build_assertions_prompt(self, context: str, schema: str) -> str:
        """
        Construct a prompt for generating SQL assertions to verify compliance.

        This method should create a prompt that instructs the LLM to generate
        executable SQL queries that check for compliance violations. Each assertion
        should return rows that represent violations (empty results mean compliance).

        The assertions will be executed by an external API or team against the actual database.

        Args:
            context (str):
                Retrieved compliance documentation relevant to the schema.
            schema (str):
                The SQL schema to generate assertions for.

        Returns:
            str: A prompt instructing the LLM to generate a list of SQL assertion queries.

        Note:
            Each assertion should:
            - Be a valid SQL SELECT query
            - Return rows only when violations exist
            - Include descriptive column aliases explaining the violation
            - Be self-contained and executable against the schema
        """
        pass

    @abstractmethod
    def _build_assertion_analysis_prompt(
        self, context: str, assertion: str, failure_result: str
    ) -> str:
        """
        Construct a prompt for analyzing a failed assertion and providing remediation.

        This method should create a prompt that helps the LLM understand why an
        assertion failed and provide specific, actionable recommendations to fix
        the compliance violation.

        Args:
            context (str):
                Retrieved compliance documentation relevant to the failed assertion.
            assertion (str):
                The SQL assertion query that failed.
            failure_result (str):
                The result returned by the failed assertion (the violating rows/data).

        Returns:
            str: A prompt instructing the LLM to analyze the failure and provide
                 specific remediation steps, including SQL fixes where applicable.

        Note:
            The prompt should guide the LLM to:
            - Explain which compliance requirement was violated
            - Reference specific clauses from the standard
            - Provide concrete SQL statements to fix the issue
            - Explain the security implications
        """
        pass

    # TODO: Remove deprecated method after the new methods work
    @deprecated(
        "Use _build_assertions_prompt() and _build_assertion_analysis_prompt() instead."
    )
    @abstractmethod
    def _build_prompt(self, context: str, schema: str) -> str:
        """
        [DEPRECATED] Construct the main compliance analysis prompt.

        This method is being deprecated in favor of the assertion-based approach.
        It remains for backward compatibility but should not be used in new code.

        Args:
            context (str):
                Retrieved compliance documentation relevant to the artifact.
            schema (str):
                The artifact to analyze (SQL schema, config file, etc.).

        Returns:
            str: A complete prompt for compliance analysis.
        """
        pass

    # TODO: Remove deprecated method after the new methods work
    @deprecated("Use generate_assertions() and analyze_failed_assertion() instead.")
    @abstractmethod
    def analyze(self, schema: str) -> str:
        """
        Perform compliance analysis on the given artifact.

        This is the main entry point for compliance checking. Subclasses should
        implement the full analysis workflow:
        1. Generate compliance questions
        2. Retrieve relevant documentation
        3. Generate SQL assertions
        4. Return assertions for external execution

        Args:
            schema (str):
                The artifact to analyze (SQL schema, config, policy, etc.).

        Returns:
            str: The generated SQL assertions as a formatted string or JSON.
        """
        pass

    def _parse_list_response(
        self, response: str, fallback_item_limit: int = 6
    ) -> list[str]:
        """
        Parse a response string that should contain a JSON list of strings.

        Args:
            response (str): The response string to parse, potentially containing markdown formatting
            fallback_item_limit (int): Maximum number of items to return when using fallback parsing

        Returns:
            list[str]: A list of strings extracted from the response
        """
        logger.debug("Raw list response: %s", repr(response))

        try:
            # Clean up potential markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith("```python3"):
                cleaned_response = cleaned_response[10:]
            elif cleaned_response.startswith("```python"):
                cleaned_response = cleaned_response[9:]
            elif cleaned_response.startswith("```py"):
                cleaned_response = cleaned_response[5:]
            elif cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```sql"):
                cleaned_response = cleaned_response[6:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]

            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            cleaned_response = cleaned_response.strip()

            items = json.loads(cleaned_response)

            if not isinstance(items, list):
                raise ValueError("Response is not a valid list.")

            logger.debug("Successfully parsed %s items from JSON", len(items))
            return items

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse response as JSON: %s", e)
            logger.warning("Raw response: %s", repr(response))

            # Fallback: extract items from text (one per line)
            lines = response.strip().split("\n")
            items = []

            for line in lines:
                cleaned_line = line.strip(" -\"[]'")
                # Only include non-empty lines with reasonable content
                if cleaned_line and len(cleaned_line) > 10:
                    items.append(cleaned_line)

            # Limit to fallback_item_limit if we have too many items
            if len(items) > fallback_item_limit:
                items = items[:fallback_item_limit]
                logger.debug("Extracted and limited to %s items from text", len(items))
            else:
                logger.debug("Extracted %s items from text", len(items))

            return items

    def _generate_schema_questions(self, schema: str) -> list[str]:
        """
        Generate targeted compliance questions from the schema using the LLM.

        This method uses the LLM to intelligently extract compliance concerns from
        the input schema. The generated questions are then used to query the
        vector store for relevant documentation, making retrieval more focused
        than direct schema-based queries.

        Args:
            schema (str):
                The SQL schema to analyze.

        Returns:
            list[str]: A list of compliance question strings. Returns up to 6 questions,
                       even if JSON parsing fails (fallback to text extraction).

        Raises:
            No exceptions are raised - parsing failures trigger fallback logic.

        Note:
            The method expects JSON output from the LLM but has robust fallback
            handling for malformed responses, including stripping markdown code blocks.
        """
        prompt = self._build_schema_questions_prompt(schema)

        # Use lower temperature for more consistent, focused question generation
        response = self.llm.generate(
            prompt, max_tokens=1024, temperature=0.3, stream=False
        )

        return self._parse_list_response(response)

    def _generate_assertion_questions(self, assertion: str) -> list[str]:
        """
        Generate targeted compliance questions from the assertion using the LLM.

        This method uses the LLM to intelligently extract compliance concerns from
        the input assertion. The generated questions are then used to query the
        vector store for relevant documentation, making retrieval more focused
        than direct assertion-based queries.

        Args:
            assertion (str):
                The SQL assertion to analyze.

        Returns:
            list[str]: A list of compliance question strings. Returns up to 2 questions,
                       even if JSON parsing fails (fallback to text extraction).

        Raises:
            No exceptions are raised - parsing failures trigger fallback logic.

        Note:
            The method expects JSON output from the LLM but has robust fallback
            handling for malformed responses, including stripping markdown code blocks.
        """
        prompt = self._build_assertion_questions_prompt(assertion)

        # Use lower temperature for more consistent, focused question generation
        response = self.llm.generate(
            prompt, max_tokens=512, temperature=0.3, stream=False
        )

        return self._parse_list_response(response, 2)

    def _retrieve_context_for_questions(
        self, questions: list[str], retrieval_k: int | None = None
    ) -> str:
        """
        Retrieve relevant compliance documentation for multiple questions.

        This method queries the vector store with each generated question and
        combines all retrieved contexts into a single comprehensive context string.
        Uses a set to automatically deduplicate retrieved document chunks.

        Args:
            questions (list[str]):
                List of compliance-related questions to search for.
            retrieval_k (int | None):
                Optional override for the number of context chunks to retrieve per question.
                When provided, this value is passed directly to `ContextRetriever.context`.
                When ``None`` (the default), the retriever's own default retrieval configuration is used.

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
                for context in self.context_retriever.context(question, retrieval_k):
                    all_contexts.add(context.page_content)
            else:
                for context in self.context_retriever.context(question):
                    all_contexts.add(context.page_content)

        combined_context = "\n\n--- Context chunks seperator ---\n\n".join(all_contexts)

        logger.info("Successfully retrieved context for %s questions", len(questions))
        return combined_context

    def generate_assertions(self, schema: str) -> list[str]:
        """
        Generate SQL assertions to verify compliance.

        This method implements the assertion generation workflow:
        1. Generate targeted compliance questions from the schema
        2. Retrieve relevant compliance documentation
        3. Generate SQL assertions based on context and schema

        Args:
            schema (str):
                The SQL database schema to generate assertions for.

        Returns:
            list[str]: A list of SQL assertion queries. Each query should return
                      rows only when violations exist (empty = compliant).

        Example:
            >>> checker = PCIComplianceChecker(model_path, chroma_dir)
            >>> assertions = checker.generate_assertions(schema)
            >>> # Execute assertions externally
            >>> for assertion in assertions:
            ...     print(assertion)
        """
        logger.info("Generating compliance questions from schema")
        questions = self._generate_schema_questions(schema)
        context = self._retrieve_context_for_questions(questions)

        prompt = self._build_assertions_prompt(context, schema)

        logger.info("Generating SQL assertions")
        response = self.llm.generate(
            prompt, max_tokens=2048, temperature=0.3, stream=False
        )

        assertions = self._parse_list_response(response, fallback_item_limit=10)
        logger.info("Successfully generated %s SQL assertions", len(assertions))

        return assertions

    def analyze_failed_assertion(
        self, assertion: str, failure_result: str
    ) -> Iterator[CreateCompletionStreamResponse]:
        """
        Analyze a failed assertion and provide remediation recommendations.

        This method analyzes why a specific assertion failed and provides
        actionable recommendations to fix the compliance violation.

        Args:
            assertion (str):
                The SQL assertion query that failed.
            failure_result (str):
                The result returned by the failed assertion (violating rows/data).

        Returns:
            Iterator[CreateCompletionStreamResponse]: An iterator yielding chunks of the
                generated analysis. This is used for streaming output.

        Example:
            >>> checker = PCIComplianceChecker(model_path, chroma_dir)
            >>> assertion = "SELECT * FROM customers WHERE cvv IS NOT NULL"
            >>> result = "id: 1, cvv: 123\\nid: 2, cvv: 456"
            >>> stream_chunks = checker.analyze_failed_assertion(assertion, result)
            >>> for chunk in stream_chunks:
            ...     token = chunk["choices"][0]["text"]
            ...     print(token, end="", flush=True)
        """
        # Generate a question to retrieve relevant context for this specific violation
        logger.info("Generating questions from failed assertion: %s", assertion)
        questions = self._generate_assertion_questions(assertion)
        context = self._retrieve_context_for_questions(questions, 4)

        logger.debug("Retrieved context: %s", context)

        prompt = self._build_assertion_analysis_prompt(
            context, assertion, failure_result
        )

        stream_chunks = self.llm.stream_chunks(prompt, max_tokens=800, temperature=0.65)

        return stream_chunks

    def analyze_failed_assertion_stdout(
        self, assertion: str, failure_result: str
    ) -> str:
        """
        Analyze a failed assertion and return the full analysis text.

        This is a convenience method that returns the complete analysis as a string,
        useful for non-streaming contexts (e.g., tests, batch processing).
        It "streams" the generation to stdout as it progresses.

        Args:
            assertion (str): The SQL assertion query that failed.
            failure_result (str): The result returned by the failed assertion.

        Returns:
            str: The complete analysis text.
        """
        logger.info("Generating questions from failed assertion: %s", assertion)
        questions = self._generate_assertion_questions(assertion)
        context = self._retrieve_context_for_questions(questions, 4)

        logger.debug("Retrieved context: %s", context)

        prompt = self._build_assertion_analysis_prompt(
            context, assertion, failure_result
        )

        logger.info("Analyzing failed assertion")
        response = self.llm.generate(
            prompt, max_tokens=800, temperature=0.65, stream=True
        )
        logger.info("Successfully analyzed failed assertion")

        return response

    def close(self):
        """
        Clean up resources used by the compliance checker.

        Releases LLM model resources and frees associated memory (GPU/CPU).
        Should be called when the compliance checker is no longer needed.

        Example:
            >>> checker = PCIComplianceChecker(model_path, chroma_dir)
            >>> try:
            ...     assertions = checker.generate_assertions(schema)
            ... finally:
            ...     checker.close()
        """
        self.llm.close()
