import json
import logging
import random
import re
import textwrap
from time import sleep
from typing import Iterator

from django.conf import settings

logger = logging.getLogger(__name__)


class MockComplianceChecker:
    """
    A lightweight mock compliance checker for development workflows.

    This class mirrors the public interface of the real `ComplianceChecker`s
    while avoiding using the LLM or vector retrieval clients at runtime.

    The responses are intentionally labeled as mock output for "Mock v1.0.0"
    so the app behavior is obvious during development.

    Example of how this class should be used:
    ```python
    from django.conf import settings

    # Put this at the bottom of the definition of the standard compliance checker
    if settings.USE_MOCK_COMPLIANCE_CHECKER:
        from watchtower_ce.engine.utils import MockComplianceChecker

        PCIComplianceChecker = MockComplianceChecker # pyright: ignore[reportAssignmentType]
    ```
    """

    # delay in seconds
    artificial_streaming_delay: float = settings.MOCK_ARTIFICIAL_STREAMING_DELAY
    artificial_processing_delay: float = settings.MOCK_ARTIFICIAL_PROCESSING_DELAY

    suppress_mock_warning: bool = settings.SUPPRESS_MOCK_COMPLIANCE_CHECKER_WARNING

    def __init__(
        self,
        collection_name: str = "Mock-v1.0.0",
        retrieval_k: int = 4,
        prompt_template: str = "<|turn>user\n{prompt}<turn|>\n<|turn>model\n",
        stop: str | list[str] | None = ["<turn|>"],
        top_k: int = 64,
    ) -> None:
        """
        Initialize the MockComplianceChecker.

        This mock implementation accepts the same parameters as the real compliance checker
        but does not perform any actual AI or vector operations. It provides lightweight
        mock responses for development and testing purposes.

        Args:
            collection_name (str):
                Name of the mock collection. Will be used as the key for the instance registry. Defaults to `"Mock-v1.0.0"`.
            retrieval_k (int):
                Mock parameter - not used in mock implementation.
                Defaults to `4`.
            prompt_template (str):
                Mock parameter - not used in mock implementation.
                Defaults to Gemma 4's format: `"<|turn>user\n{prompt}<turn|>\n<|turn>model\n"`.
            stop (str | list[str] | None):
                Mock parameter - not used in mock implementation.
                Defaults to `["<turn|>"]`.
            top_k (int):
                Mock parameter - not used in mock implementation.
                Defaults to `64`.
        """
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._initialized: bool = True
        self.collection_name: str = collection_name
        self.standard: str = f"Mock {collection_name}"

        if not self.suppress_mock_warning:
            logger.warning(
                "Using MockComplianceChecker for '%s' instead of a real compliance checker. "
                "Set WTCE_USE_MOCK_COMPLIANCE_CHECKER=false in to disable the mock, "
                "or set WTCE_SUPPRESS_MOCK_COMPLIANCE_CHECKER_WARNING=True to silence this warning.",
                collection_name,
            )

    def _parse_list_response(
        self, response: str, fallback_item_limit: int = 6
    ) -> list[str]:
        """
        Parse a JSON response string into a list of strings.

        Args:
            response (str): The JSON string to parse.
            fallback_item_limit (int): Unused parameter for compatibility. Defaults to 6.

        Returns:
            list[str]: The parsed list of strings.

        Raises:
            ValueError: If the response is not a valid JSON list.
        """
        logger.debug("Raw list response: %s", repr(response))

        cleaned_response = response.replace("\n", " ")
        cleaned_response = cleaned_response.strip()
        items = json.loads(cleaned_response)

        if not isinstance(items, list):
            raise ValueError("Response is not a valid list.")

        logger.debug("Successfully parsed %s items from JSON", len(items))
        return items

    def _extract_table_names(self, schema: str) -> list[str]:
        """
        Extract table names from a SQL schema string using regex.

        Args:
            schema (str): The SQL schema string to parse.

        Returns:
            list[str]: List of extracted table names.
        """
        return re.findall(
            textwrap.dedent(
                r"""
                CREATE\s+TABLE\s+
                (?P<name>
                    (?:
                        ["`]?[A-Za-z0-9_]+["`]?\.
                    )?
                        ["`]?[A-Za-z0-9_]+["`]?
                )
                """
            ),
            schema,
            flags=re.IGNORECASE | re.VERBOSE,
        )

    def _mock_assertions_from_schema(self, schema: str) -> list[str]:
        """
        Generate mock SQL assertions based on the provided schema.

        Args:
            schema (str): The SQL schema string.

        Returns:
            list[str]: List of mock SQL assertion queries.
        """
        if not schema.strip():
            return []

        table_names = self._extract_table_names(schema)
        if table_names:
            first_table = table_names[0]
            return [
                f"SELECT 1 AS mock_compliance_check FROM {first_table} WHERE 1 = 0;",
                f"SELECT 1 AS mock_violation FROM {first_table} WHERE 1 = 1;",
            ]

        return [
            "SELECT 1 AS mock_compliance_check WHERE 1 = 0;",
            "SELECT 1 AS mock_violation WHERE 1 = 1;",
        ]

    def _mock_analysis_text(self, assertion: str, failure_result: str) -> str:
        """
        Generate mock analysis text for a failed assertion.

        Args:
            assertion (str): The failed SQL assertion.
            failure_result (str): Unused parameter for compatibility.
                                  The result of the failed assertion.

        Returns:
            str: Mock analysis text describing the failure.
        """
        return textwrap.dedent(
            f"""
            ## VIOLATION SUMMARY
            {self.standard} analysis for failed assertion.
            This is a simulated remediation summary, not a real standard.

            Failed assertion: `{assertion}`

            ## STANDARD REFERENCE
            This violates {self.standard} control 1.1: "Mock controls are not real controls."

            ## SECURITY IMPACT
            Non-compliance with {self.standard} may lead to undetected mock violations and a false sense of security during development.

            ## REMEDIATION STEPS
            1. Recognize that this is a mock violation and does not reflect real compliance status.
            2. Use this mock output to test the application's handling of compliance failures.
            3. Use this code block to test markdown formatting for it:

            ```sql
            DELETE FROM mock_table WHERE id = 1;

            SELECT mock_column1
            FROM mock_table
            WHERE mock_column2 > (
                SELECT AVG(mock_column2) FROM mock_table
            );
            ```

            4. Turn off mock compliance checker in production.

            The rest of the text here is to generate more tokens for testing streaming behaviour. Lorem ipsum dolor sit amet,
            consectetur adipiscing elit. Sed sed sagittis tortor. Nunc lobortis tincidunt cursus. Nulla maximus aliquet mi,
            eget vestibulum neque. Phasellus feugiat purus ac est posuere euismod. Nunc maximus gravida neque, ut accumsan
            mi congue mattis. Morbi consequat fringilla tempor. Vivamus varius placerat sapien, vitae vulputate eros pellentesque
            non. Cras fringilla est eu arcu tempus, quis elementum ipsum semper. Pellentesque efficitur mauris sed nulla
            ornaresagittis. Vestibulum suscipit turpis sit amet malesuada pharetra. Proin ac dolor ac orci egestas interdum
            nec vel ipsum. Curabitur id mi velit. Vestibulum a metus in neque placerat pellentesque id sit amet magna.

            Fusce faucibus consectetur semper. Aenean aliquet semper lorem, vitae luctus ipsum. Phasellus semper, ipsum nec
            hendrerit cursus, augue nulla ultricies ipsum, eu faucibus quam odio eu diam. Maecenas mattis elementum massa imperdiet
            pulvinar. Etiam quis tortor auctor, ullamcorper risus eu, consectetur sapien. Aenean ex turpis, pharetra vitae iaculis
            et, gravida id urna. Cras vehicula massa odio, ac ullamcorper diam lacinia quis. Pellentesque condimentum, tortor
            varius vestibulum mattis, dolor lectus elementum lacus, ac luctus libero sem et odio. Nulla sollicitudin eros nunc,
            molestie congue nulla semper feugiat.
            """
        ).strip()

    def _stream_tokens(
        self, text: str, chunk_size_range: tuple[int, int] = (2, 10)
    ) -> Iterator[str]:
        """
        Stream text in randomized chunks for realistic mock token generation.

        Args:
            text (str): The text to stream.
            chunk_size_range (tuple[int, int]): Min and max characters per chunk.
                                              Defaults to (2, 10).

        Yields:
            str: Randomized chunks of the text.
        """
        pos = 0
        while pos < len(text):
            chunk_size = random.randint(*chunk_size_range)
            yield text[pos : pos + chunk_size]
            pos += chunk_size

    def generate_assertions(self, schema: str) -> list[str]:
        """
        Generate mock SQL assertions for the given schema.

        Args:
            schema (str): The SQL schema to generate assertions for.

        Returns:
            list[str]: List of mock SQL assertion queries.
        """
        logger.info(
            "Mock generate_assertions called with schema length %s",
            len(schema),
        )
        sleep(self.artificial_processing_delay)  # Simulate processing delay
        return self._mock_assertions_from_schema(schema)

    def analyze_failed_assertion(
        self,
        assertion: str,
        failure_result: str,
    ) -> Iterator:
        """
        Analyze a failed assertion and yield mock analysis chunks.

        Args:
            assertion (str): The failed SQL assertion.
            failure_result (str): The result of the failed assertion.

        Yields:
            dict: Mock analysis chunks in the format expected by the caller.
        """
        logger.info(
            "Mock analyze_failed_assertion called for assertion: %s",
            assertion,
        )
        sleep(
            self.artificial_processing_delay
        )  # Simulate processing delay for generating the assertion questions
        analysis_text = self._mock_analysis_text(assertion, failure_result)

        for chunk in self._stream_tokens(analysis_text):
            sleep(self.artificial_streaming_delay)  # Simulate streaming delay
            yield {"choices": [{"text": chunk}]}

    def analyze_failed_assertion_stdout(
        self,
        assertion: str,
        failure_result: str,
    ) -> str:
        """
        Analyze a failed assertion, stream the analysis to stdout,
        and return mock analysis as a string.

        Args:
            assertion (str): The failed SQL assertion.
            failure_result (str): The result of the failed assertion.

        Returns:
            str: Mock analysis text.
        """
        logger.info(
            "Mock analyze_failed_assertion_stdout called for assertion: %s", assertion
        )
        sleep(
            self.artificial_processing_delay
        )  # Simulate processing delay for generating the assertion questions
        analysis_text = self._mock_analysis_text(assertion, failure_result)

        for chunk in self._stream_tokens(analysis_text):
            sleep(self.artificial_streaming_delay)  # Simulate streaming delay
            print(chunk, end="", flush=True)

        return self._mock_analysis_text(assertion, failure_result)

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text (mock implementation).

        Args:
            text (str): The text to count tokens in.

        Returns:
            int: The number of tokens (words in this mock).
        """
        return len(text.split())

    def close(self) -> None:
        """
        Close the mock compliance checker (no-op for mock implementation).
        """
        logger.debug("Mock compliance checker close called")
