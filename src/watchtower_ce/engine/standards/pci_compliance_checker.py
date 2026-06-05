import textwrap

from ..core.compliance_checker import ComplianceChecker


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
        return textwrap.dedent(
            # TODO: Refine ALL prompts with respect to the new more powerful model.
            f"""
            You are an expert PCI-DSS compliance auditor and database security specialist.

            Task:
            Analyze the SQL schema and infer possible {self.standard} concerns.
            Generate ONLY 3-6 comprehensive rich questions an auditor would ask that
            directly relate to the following PCI-DSS requirements:
            - Requirement 3: Storage and protection of stored cardholder data (e.g., PAN, SAD, hashing, encryption, truncation)
            - Requirement 4: Protection of cardholder data during transmission (encryption in transit, key management assumptions)
            - Requirement 7: Restriction of access to cardholder data by business need-to-know
            - Requirement 8: Identification and authentication of users accessing cardholder data
            - Requirement 10: Logging, monitoring, and audit trails for access to cardholder data

            Instructions:
            1. Examine the schema for both clear (e.g., "credit_card") and ambiguous (e.g., "blob_data", "user_info") columns.
            2. Generate questions that use PCI-DSS terminology (e.g., "PAN" instead of "card number", "SAD" instead of "security code", etc.).
            3. Be specific (e.g., PAN and SAD are not the same thing and should be treated as so in your questions;
               these are two separate topics, so two separate questions if needed).
            4. Avoid using raw database field names in the questions; translate them into natural English descriptions (e.g., "card number" instead of "card_number", etc.).
            5. Ensure questions are retrieval friendly to vector stores. They should sound like they are seeking specific guidance from the standard.

            Response:
            - Respond ONLY with a valid JSON list of strings containing the questions.
            - Ensure the output is valid JSON and respects proper escaping.
            - MAXIMUM 6 questions.
            - Do NOT include any comments of any kind, introductory text, or any markdown formatting.

            Output example:
            ["<question 1>", "<question 2>", ...]

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
            str: A formatted prompt instructing the LLM to generate 2 comprehensive
                 questions as a JSON list of strings.
        """
        return textwrap.dedent(
            f"""
            You are an expert PCI-DSS compliance auditor and database security specialist.

            Task:
            Analyze the SQL assertion command and infer possible {self.standard} concerns.
            Generate ONLY 4 comprehensive rich questions depending on what the assertion command checks for that an auditor would ask that directly relate to the following PCI-DSS requirements:
            - Requirement 3: Storage and protection of stored cardholder data (e.g., PAN, SAD, hashing, encryption, truncation)
            - Requirement 4: Protection of cardholder data during transmission (encryption in transit, key management assumptions)
            - Requirement 7: Restriction of access to cardholder data by business need-to-know
            - Requirement 8: Identification and authentication of users and administrators accessing system components (password hashing, MFA)
            - Requirement 10: Logging, monitoring, and audit trails for access to cardholder data

            Instructions:
            1. Examine the assertion for both clear (e.g., "credit_card") and ambiguous (e.g., "blob_data", "user_info") columns.
            2. Generate questions that use PCI-DSS terminology (e.g., "PAN" instead of "card number", "SAD" instead of "security code", etc.).
            3. Be specific (e.g., PAN and SAD are not the same thing and should be treated as so in your questions;
               these are two separate topics, so two separate questions if needed).
            4. Avoid using raw database field names in the questions; translate them into natural English descriptions (e.g., "card number" instead of "card_number", etc.).
            5. End your questions with "according to requirement <requirement number you are asking about> ?"
            6. Ensure questions are retrieval friendly to vector stores. They should be written with many keywords to help with searching.

            Output:
            - Respond ONLY with a valid JSON list of strings containing the questions.
            - Ensure the output is valid JSON and respects proper escaping.
            - EXACTLY 4 questions.
            - Do NOT include any comments of any kind, introductory text, or any markdown formatting.

            Output example:
            ["<question 1>", "<question 2>", "<question 3>", "<question 4>"]

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
        # TODO: Experiment with changing
        # "- Include descriptive column aliases explaining the violation"
        # to
        # "- Be as simple and direct as possible while still being effective at identifying violations"
        return textwrap.dedent(
            f"""
            You are an expert PCI-DSS compliance auditor and SQL specialist.

            Context chunks (retrieved from a {self.standard} standard vector store):
            {context}

            Task:
            Generate SQL assertions to verify {self.standard} compliance for the schema below.
            Each assertion must be a SELECT query that returns rows ONLY when violations exist.
            Empty results mean compliance.

            Focus on:
            1. Detecting unencrypted cardholder data (PANs stored in plaintext)
            2. Detecting prohibited sensitive authentication data (CVV, PIN, full track data)
            3. Verifying encryption/hashing is applied to sensitive columns
            4. Checking for audit logging capabilities (created_at, updated_at, etc.)
            5. Identifying columns with ambiguous names that might store payment data
            6. Verifying access controls exist (not just public tables)

            Requirements for each assertion:
            - Must be a valid SELECT query
            - Should return violating rows/columns, or designed to return empty results if compliant
            - Include descriptive column aliases explaining the violation
            - Be executable against the provided schema
            - Focus on one specific compliance check

            SQL Schema:
            {schema}

            Output:
            - Generate as many assertions as you need against the provided schema covering different {self.standard} requirements when necessary.
            - Respond **ONLY** with a valid JSON list of strings containing the SQL queries.
            - Ensure the output is valid JSON and respects proper escaping.
            - Do NOT include any comments of any kind, introductory text, or any markdown formatting.

            Output example:
            ["<assertion SQL query 1>", "<assertion SQL query 2>", ...]
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
        return textwrap.dedent(
            f"""
            You are an expert PCI-DSS compliance auditor and database security specialist.

            Context chunks (retrieved from a {self.standard} standard vector store; often not all of it is needed. Pick only what's relevant):
            {context}

            A compliance assertion has FAILED, indicating a {self.standard} violation.

            Failed Assertion:
            {assertion}

            Violation Details (rows returned by assertion):
            {failure_result}

            Task:
            Analyze this failure and provide specific remediation guidance.

            Your response must include:
            1. VIOLATION SUMMARY: What specific {self.standard} requirement is violated
            2. STANDARD REFERENCE: Cite the exact {self.standard} clause(s) that apply
            3. SECURITY IMPACT: Explain the risk this violation poses to cardholder data
            4. REMEDIATION STEPS: Provide concrete, actionable steps and optionally SQL queries to fix this violation

            Your reply should:
            - Use as much wording from the given context as possible except for the REMEDIATION STEPS.
            - Be specific and actionable. If encryption is needed, specify what to encrypt and how.
              If data should be deleted, explain why and provide the SQL to do so safely. And so on.
            """
        ).strip()
