from textwrap import dedent

from django.conf import settings

from ..core import ComplianceChecker


class PCIComplianceChecker(ComplianceChecker):
    """
    PCI-DSS compliance analyzer for SQL database schemas using assertion-based RAG.

    This specialized compliance checker generates SQL assertions to verify PCI-DSS
    compliance in database schemas. The assertions are executed externally, and
    failed assertions are analyzed to provide specific remediation recommendations.

    The checker focuses on:
    - Cardholder data storage (PAN, CVV, expiration dates)
    - Sensitive authentication data retention (violates PCI-DSS)
    - Encryption and hashing requirements
    - Access control mechanisms
    - Audit logging capabilities
    - Ambiguous column names that might contain payment data

    Attributes:
        standard (str):
            The compliance standard being checked ("PCI-DSS v4.0.1").
    """

    standard: str = "PCI-DSS v4.0.1"

    def _get_system_prompt(self) -> str:
        """
        Return the default system prompt for PCI-DSS compliance auditing.
        """
        return dedent(
            f"""
            You are an expert {self.standard} compliance auditor and database security specialist.
            Your role is to identify potential security risks and compliance violations within SQL database schemas and assertions.

            Definitions:
            - Assertion: A `SELECT` SQL statement that returns rows ONLY when a compliance violation is detected. An empty result indicates full compliance.
            - Failure Result: The output of an assertion that indicates a violation of {self.standard} complaince requirements.

            Core {self.standard} Requirements to Audit:
            - Requirement 3: Storage and protection of stored cardholder data (e.g., PAN, SAD, hashing, encryption, truncation)
            - Requirement 4: Protection of cardholder data during transmission (encryption in transit, key management assumptions)
            - Requirement 7: Restriction of access to cardholder data by business need-to-know
            - Requirement 8: Identification and authentication of users and administrators accessing system components
            - Requirement 10: Logging, monitoring, and audit trails for access to cardholder data

            General Instructions:
            1. Always use precise {self.standard} terminology (e.g., "PAN", "SAD", "Cardholder Data").
            2. You'll only ever respond either in markdown or JSON.
            3. When generating lists (questions or assertions), always respond with a valid JSON list of strings.
            4. Do NOT include any introductory text, comments, or markdown formatting in JSON responses.
            5. Do NOT respond with more than what is requested. Follow the format requested by the user.
            6. Do NOT wrap your whole response in ```json``` or ```markdown``` code blocks when responding in JSON or markdown format, respectively. You may use them only for code snippets or when explicitly requested by the user.
            7. Ensure all SQL generated is valid and executable against the provided schema with respect to its database dialect (either PostgreSQL or MySQL).
            """
        ).strip()

    def _build_schema_questions_prompt(self, schema: str) -> str:
        """
        Build a prompt for generating PCI-DSS specific compliance questions.

        Creates a prompt that instructs the LLM to analyze a SQL schema and generate
        targeted questions about PCI-DSS concerns. The questions focus on cardholder
        data handling, sensitive authentication data, encryption requirements, and
        potential ambiguous columns.

        Args:
            schema (str):
                The SQL schema to analyze.

        Returns:
            str: A formatted prompt instructing the LLM to generate 3-6 comprehensive
                 questions as a JSON list of strings.
        """
        return dedent(
            f"""
            Task:
            - Analyze the SQL schema and infer possible {self.standard} concerns.
            - Generate ONLY 3-6 comprehensive rich questions an auditor would ask that directly relate to the core {self.standard} requirements.

            Instructions:
            1. Examine the schema for both clear (e.g., "credit_card") and ambiguous (e.g., "blob_data", "user_info") columns.
            2. Be specific (e.g., PAN and SAD are not the same thing and should be treated as so in your questions).
            3. Avoid using raw database field names in the questions; translate them into natural English descriptions.
            4. Ensure questions are retrieval friendly to vector stores. They should sound like they are seeking specific guidance from the standard.

            Output Format:
            - Respond with a valid JSON list of strings (the questions).
            - MAXIMUM 6 questions.

            Example Output:
            ["Question 1 ?", "Question 2 ?", ...]

            Schema:
            {schema}
            """
        ).strip()

    def _build_assertion_questions_prompt(self, assertion: str) -> str:
        """
        Build a prompt for generating PCI-DSS specific compliance questions.

        Creates a prompt that instructs the LLM to analyze an SQL assertion and generate
        targeted questions about PCI-DSS concerns. The questions focus on cardholder
        data handling, sensitive authentication data, encryption requirements, and
        potential ambiguous columns.

        Args:
            assertion (str):
                The SQL assertion to analyze.

        Returns:
            str: A formatted prompt instructing the LLM to generate 4 comprehensive
                 questions as a JSON list of strings.
        """
        return dedent(
            f"""
            Task:
            - Analyze the SQL assertion command and infer possible {self.standard} concerns.
            - Generate ONLY 3 comprehensive rich questions depending on what the assertion command checks for that an auditor would ask that directly relate to the core {self.standard} requirements.

            Instructions:
            1. Examine the assertion for both clear (e.g., "credit_card") and ambiguous (e.g., "blob_data", "user_info") columns.
            2. Be specific (e.g., PAN and SAD are not the same thing and should be treated as so in your questions).
            3. Avoid using raw database field names in the questions; translate them into natural English descriptions.
            4. End your questions with "according to requirement <requirement number you are asking about> ?"
            5. Ensure questions are retrieval friendly to vector stores. They should be written with many keywords to help with searching.

            Output Format:
            - Respond with a valid JSON list of strings (the questions).
            - EXACTLY 3 questions.

            Example Output:
            ["Question 1 ?", "Question 2 ?", "Question 3 ?"]

            Assertion:
            {assertion}
            """
        ).strip()

    def _build_assertions_prompt(self, context: str, schema: str) -> str:
        """
        Build a prompt for generating SQL assertions to verify PCI-DSS compliance.

        Creates a prompt that instructs the LLM to generate executable SQL queries
        that check for PCI-DSS violations. Each assertion returns rows only when
        violations exist (empty results indicate compliance).

        Args:
            context (str):
                Retrieved PCI-DSS documentation relevant to the schema.
            schema (str):
                The SQL schema to generate assertions for.

        Returns:
            str: A formatted prompt instructing the LLM to generate SQL assertions
                 as a JSON list of strings. Each assertion is a SELECT query that
                 identifies compliance violations.
        """
        return dedent(
            f"""
            Context chunks (retrieved from a {self.standard} standard vector store):
            {context}

            Task:
            Generate SQL assertions to verify {self.standard} compliance for the schema below.
            Each assertion must be a SELECT query that returns rows ONLY when violations exist.
            Empty results mean compliance.

            Focus on:
            1. Detecting unencrypted cardholder data (PANs stored in plaintext).
            2. Detecting prohibited sensitive authentication data (CVV, PIN, full track data).
            3. Verifying encryption/hashing is applied to sensitive columns.
            4. Checking for audit logging capabilities (created_at, updated_at, etc.).
            5. Identifying columns with ambiguous names that might store payment data.
            6. Verifying access controls exist (not just public tables).

            Instructions:
            - Each assertion must be a valid SELECT query. Assertions should not be generic examples; they should be runnable against the provided schema.
            - Include descriptive column aliases explaining the potential violation.
            - Generate as many assertions as you need against the provided schema. Aim for the highest coverage of the schema against the highest coverage of compliance requirements using the highest amount of assertions possible.
            - Do NOT generate one assertion that covers multiple compliance requirements. One big assertion that covers many compliance requirements is not acceptable.
            - Do NOT generate assertions that cover unrelated database errors or non-compliance issues.
            - Make sure to cover all relevant compliance requirements, and all relevant parts of the database schema.

            Output Format:
            - Respond with a valid JSON list of strings containing the SQL queries.

            Example Output:
            ["SELECT ...", "SELECT ...", ...]

            SQL Schema:
            {schema}
            """
        ).strip()

    def _build_assertion_analysis_prompt(
        self, context: str, assertion: str, failure_result: str
    ) -> str:
        """
        Build a prompt for analyzing a failed PCI-DSS assertion.

        Creates a prompt that helps the LLM understand why an assertion failed and
        provide specific remediation recommendations with SQL examples.

        Args:
            context (str):
                Retrieved PCI-DSS documentation relevant to the failed assertion.
            assertion (str):
                The SQL assertion query that failed.
            failure_result (str):
                The result returned by the failed assertion (violating rows/data).

        Returns:
            str: A formatted prompt instructing the LLM to analyze the failure and
                 provide specific remediation steps including SQL fixes.
        """
        return dedent(
            f"""
            Context Chunks (retrieved from the {self.standard} vector store; use only relevant portions):
            {context}

            A compliance assertion has failed, indicating a {self.standard} violation.

            Failed Assertion:
            {assertion}

            Rows Returned by the Assertion:
            {failure_result}

            Task:
            Analyze the violation and provide remediation guidance.

            Instructions:
            - Base the analysis on the provided context.
            - Use as much wording from the given context as possible.
            - If the context does not provide sufficient detail, use your own knowledge to fill in the gaps.
            - Organize the response using markdown into clear, sectioned sections, with subsections when appropriate.
            - Use markdown skillfully to structure the response.
            - Wrap SQL queries in code blocks.
            - Be specific and actionable.
            - Omit any personal or sensitive information; replace it with placeholders (e.g., ****).
            - Do not mention the context directly; use the context to explain why the assertion failed, or call it the "standard".

            Output Format:

            ## Violation Summary
            A high-level summary of the violation.

            ## Standard Reference
            Cite the exact {self.standard} requirement(s) and clause(s) that apply.

            ## Detailed Analysis
            Explain why the assertion failed from a compliance perspective and what was observed.
            This section is your chance to be as verbose as possible, and get in as much detail as possible.
            Multiple paragraphs are encouraged.

            ## Security Impact
            Describe the risk and potential consequences of non-compliance on the organization.

            ## Remediation Steps
            Provide concrete actions to resolve the issue.
            Include actionable SQL queries examples based on what you know of the schema from the assertion, if relevant.

            ## Additional Notes
            Any additional context or considerations relevant to the violation. This section is optional.
            """
        ).strip()


if settings.USE_MOCK_COMPLIANCE_CHECKER:
    from ..utils import MockComplianceChecker

    PCIComplianceChecker = MockComplianceChecker  # pyright: ignore[reportAssignmentType]
