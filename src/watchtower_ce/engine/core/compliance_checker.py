import logging
from abc import ABC, abstractmethod
from typing import Iterator, Optional

from ..clients import ContextRetriever, LLMInference
from ..utils import parse_list_response, retrieve_context_for_questions

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
    """

    def __init__(
        self,
        collection_name: str,
        retrieval_k: int = 4,
        stop: Optional[str | list[str]] = None,
        top_k: int = 64,
    ) -> None:
        """
        Initialize the compliance checker with RAG components.

        Args:
            collection_name (str):
                Name of the Chroma collection with compliance documents.
            retrieval_k (int):
                Number of similar documents to retrieve per query. Defaults to `4`.
            stop (Optional[str | list[str]]):
                Custom stop sequences for generation. Defaults to `None`.
            top_k (int):
                The number of highest probability tokens to keep for top-k sampling.
                Higher values increase diversity but may reduce coherence. Defaults to `64`, Gemma 4's default.
        """
        self._context_retriever = ContextRetriever(
            collection_name=collection_name,
            retrieval_k=retrieval_k,
        )
        self._llm = LLMInference(
            system_prompt=self._get_system_prompt(),
            stop=stop,
            top_k=top_k,
        )

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """
        Return the default system prompt for the specific compliance standard.

        Subclasses must implement this to provide a persistent persona and
        general instructions for the LLM.

        Returns:
            str: The standard-specific default system prompt.
        """
        pass

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
        # TODO: Remove these debug warnings
        logger.warning(
            "Schema questions prompt token count: %d", self._llm.count_tokens(prompt)
        )

        response = self._llm.generate(
            prompt, max_tokens=1024, temperature=1, stream=False
        )

        return parse_list_response(response, 6)

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
            list[str]: A list of compliance question strings. Returns up to 3 questions,
                       even if JSON parsing fails (fallback to text extraction).

        Raises:
            No exceptions are raised - parsing failures trigger fallback logic.

        Note:
            The method expects JSON output from the LLM but has robust fallback
            handling for malformed responses, including stripping markdown code blocks.
        """
        prompt = self._build_assertion_questions_prompt(assertion)
        logger.warning(
            "Assertion questions prompt token count: %d", self._llm.count_tokens(prompt)
        )

        response = self._llm.generate(
            prompt, max_tokens=2048, temperature=1, stream=False
        )

        return parse_list_response(response, 3)

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
            >>> checker = PCIComplianceChecker(collection_name="PCI-DSS-v4.0.1")
            >>> assertions = checker.generate_assertions(schema)
            >>> # Execute assertions externally
            >>> for assertion in assertions:
            ...     print(assertion)
        """
        logger.info("Generating compliance questions from schema")
        questions = self._generate_schema_questions(schema)
        context = retrieve_context_for_questions(self._context_retriever, questions, 2)

        prompt = self._build_assertions_prompt(context, schema)
        logger.warning(
            "Assertions prompt token count: %s", self._llm.count_tokens(prompt)
        )

        logger.info("Generating SQL assertions")
        response = self._llm.generate(
            prompt, max_tokens=2048, temperature=0.6, stream=False
        )

        assertions = parse_list_response(response, 20)
        logger.info("Successfully generated %s SQL assertions", len(assertions))

        return assertions

    def analyze_failed_assertion(
        self, assertion: str, failure_result: str
    ) -> Iterator[dict]:
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
            Iterator[dict]: An iterator yielding chunks of the
                generated analysis. This is used for streaming output.

        Example:
            >>> checker = PCIComplianceChecker(collection_name="PCI-DSS-v4.0.1")
            >>> assertion = "SELECT * FROM customers WHERE cvv IS NOT NULL"
            >>> result = "id: 1, cvv: 123\\nid: 2, cvv: 456"
            >>> stream_chunks = checker.analyze_failed_assertion(assertion, result)
            >>> for chunk in stream_chunks:
            ...     token = chunk["choices"][0]["text"]
            ...     print(token, end="", flush=True)
        """
        logger.info("Generating questions from failed assertion: %s", assertion)
        questions = self._generate_assertion_questions(assertion)
        context = retrieve_context_for_questions(self._context_retriever, questions, 2)

        logger.debug("Retrieved context: %s", context)

        prompt = self._build_assertion_analysis_prompt(
            context, assertion, failure_result
        )
        logger.warning(
            "Assertion analysis prompt token count: %s", self._llm.count_tokens(prompt)
        )
        logger.warning("FINAL Prompt: %s", prompt)

        yield from self._llm.stream_chunks(prompt, max_tokens=2048, temperature=1.3)

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
        context = retrieve_context_for_questions(self._context_retriever, questions, 2)

        logger.debug("Retrieved context: %s", context)

        prompt = self._build_assertion_analysis_prompt(
            context, assertion, failure_result
        )
        logger.warning(
            "Assertion analysis prompt token count: %s", self._llm.count_tokens(prompt)
        )
        logger.warning("FINAL Prompt: %s", prompt)

        logger.info("Analyzing failed assertion")
        response = self._llm.generate(
            prompt, max_tokens=2048, temperature=1, stream=True
        )
        logger.info("Successfully analyzed failed assertion")

        return response

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a string using the model's native tokenizer.

        This is useful for ensuring inputs stay within a model's context_window.

        Note: If using this method in a debug logging statement, it's best to add a check for whether
        debug logging is enabled before calling this method (e.g., `if logger.isEnabledFor(logging.DEBUG):`),
        as tokenization can be computationally expensive.

        Args:
            text (str): The text to count tokens for.

        Returns:
            int: The token count.
        """
        return self._llm.count_tokens(text)
