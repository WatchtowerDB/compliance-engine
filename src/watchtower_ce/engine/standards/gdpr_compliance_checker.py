from textwrap import dedent

from django.conf import settings

from ..core import ComplianceChecker


class GDPRComplianceChecker(ComplianceChecker):
    """
    GDPR compliance analyzer for SQL database schemas using assertion-based RAG.

    This specialized compliance checker generates SQL assertions to verify GDPR
    compliance in database schemas. The assertions are executed externally, and
    failed assertions are analyzed to provide specific remediation recommendations.

    The checker focuses on:
    - Personal data storage and minimisation (names, emails, identifiers, special categories)
    - Sensitive/special category data retention (health, biometric, racial origin, etc.)
    - Columns that may indicate criminal convictions or offences
    - Pseudonymisation and encryption requirements
    - Consent and purpose-limitation mechanisms
    - Right-to-erasure ("right to be forgotten") support
    - Audit logging and accountability capabilities
    - Ambiguous column names that might contain personal data

    Attributes:
        standard (str):
            The compliance standard being checked ("GDPR").
    """

    standard: str = "GDPR"

    def _get_system_prompt(self) -> str:
        """
        Return the default system prompt for GDPR compliance auditing.
        """
        return dedent(
            # Will verify and change later
            f"""
            You are an expert {self.standard} compliance auditor and database security specialist.
            Your role is to identify potential privacy risks and compliance violations within SQL database schemas and assertions.

            Definitions:
            - Assertion: A `SELECT` SQL statement that returns rows ONLY when a compliance violation is detected. An empty result indicates full compliance.
            - Failure Result: The output of an assertion that indicates a violation of {self.standard} complaince requirements.

            Core {self.standard} Requirements to consider:
            - Article 5: Principles of lawfulness, purpose limitation, data minimisation, accuracy, storage limitation, and integrity & confidentiality.
            - Article 9: Prohibition and conditions for processing special categories of personal data (health, biometric, racial/ethnic origin, etc.).
            - Article 10: Processing of personal data relating to criminal convictions and offences.
            - Article 17: Right to erasure ("right to be forgotten") — ability to delete a data subject's personal data on request.
            - Article 25: Data protection by design and by default — pseudonymisation, minimisation built into schema design.
            - Article 32: Security of processing — encryption, pseudonymisation, resilience, and ongoing evaluation of measures.

            General Instructions:
            1. Always use precise {self.standard} terminology (e.g., "data subject", "personal data", "special category data").
            2. You'll only ever respond either in markdown or JSON.
            3. When generating lists (questions or assertions), always respond with a valid JSON list of strings.
            4. Do NOT include any introductory text, comments, or markdown formatting in JSON responses.
            5. Do NOT respond with more than what is requested. Follow the format requested by the user.
            6. Ensure all SQL generated is valid and executable against the provided schema with respect to its database dialect (either PostgreSQL or MySQL).
            """
        ).strip()

    def _build_schema_questions_prompt(self, schema: str) -> str:
        """
        Build a prompt for generating GDPR specific compliance questions.

        Creates a prompt that instructs the LLM to analyze a SQL schema and generate
        targeted questions about GDPR concerns. The questions focus on personal
        data handling, consent mechanisms, encryption/pseudonymisation requirements,
        data minimisation, storage limitation, and potentially ambiguous columns.

        Args:
            schema (str):
                The SQL schema to analyze.

        Returns:
            str: A formatted prompt instructing the LLM to generate 3-6 comprehensive
                 questions as a JSON list of strings.
        """
        return dedent(
            # TODO: Refine ALL prompts with respect to the new more powerful model.
            f"""
            You are an expert GDPR compliance auditor and database security specialist.

            Task:
            Analyze the SQL schema and infer possible {self.standard} concerns.
            Generate ONLY 3-6 comprehensive rich questions an auditor would ask that
            directly relate to the following GDPR requirements:
            - Article 5: Principles of lawfulness, purpose limitation, data minimisation, accuracy, storage limitation, and integrity & confidentiality
            - Article 9: Prohibition and conditions for processing special categories of personal data (health, biometric, racial/ethnic origin, etc.)
            - Article 10: Processing of personal data relating to criminal convictions and offences
            - Article 17: Right to erasure ("right to be forgotten") — ability to delete a data subject's personal data on request
            - Article 25: Data protection by design and by default — pseudonymisation, minimisation built into schema design
            - Article 32: Security of processing — encryption, pseudonymisation, resilience, and ongoing evaluation of measures

            Instructions:
            1. Examine the schema for both clear (e.g., "email", "date_of_birth") and ambiguous (e.g., "blob_data", "user_info") columns that may hold personal data.
            2. Generate questions that use GDPR terminology (e.g., "data subject", "personal data", "special category data", "pseudonymisation", "lawful basis", "purpose limitation", etc.).
            3. Be specific (e.g., special category data and ordinary personal data are not the same thing and should be treated as so in your questions;
                these are two separate topics, so two separate questions if needed).
            4. Avoid using raw database field names in the questions; translate them into natural English descriptions (e.g., "date of birth" instead of "dob", etc.).
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
        Build a prompt for generating GDPR specific compliance questions.

        Creates a prompt that instructs the LLM to analyze an SQL assertion and generate
        targeted questions about GDPR concerns. The questions focus on personal data
        handling, special category data, pseudonymisation/encryption requirements,
        data subject rights, and storage limitation.

        Args:
            assertion (str):
                The SQL assertion to analyze.

        Returns:
            str: A formatted prompt instructing the LLM to generate 4 comprehensive
                 questions as a JSON list of strings.
        """
        return dedent(
            f"""
            You are an expert GDPR compliance auditor and database security specialist.

            Task:
            Analyze the SQL assertion command and infer possible {self.standard} concerns.
            Generate ONLY 4 comprehensive rich questions depending on what the assertion command checks for that an auditor would ask that directly relate to the following GDPR requirements:
            - Article 5: Principles of lawfulness, purpose limitation, data minimisation, accuracy, storage limitation, and integrity & confidentiality
            - Article 9: Prohibition and conditions for processing special categories of personal data (health, biometric, racial/ethnic origin, etc.)
            - Article 10: Processing of personal data relating to criminal convictions and offences
            - Article 17: Right to erasure ("right to be forgotten") — ability to delete a data subject's personal data on request
            - Article 25: Data protection by design and by default — pseudonymisation, minimisation built into schema design
            - Article 32: Security of processing — encryption, pseudonymisation, resilience, and ongoing evaluation of measures

            Instructions:
            1. Examine the assertion for both clear (e.g., "email", "health_record") and ambiguous (e.g., "blob_data", "user_info") columns that may hold personal data.
            2. Generate questions that use GDPR terminology (e.g., "data subject", "personal data", "special category data", "pseudonymisation", "lawful basis", "purpose limitation", etc.).
            3. Be specific (e.g., special category data and ordinary personal data are not the same thing and should be treated as so in your questions;
                these are two separate topics, so two separate questions if needed).
            4. Avoid using raw database field names in the questions; translate them into natural English descriptions (e.g., "date of birth" instead of "dob", etc.).
            5. End your questions with "according to Article <article number you are asking about> of the GDPR?"
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
        Build a prompt for generating SQL assertions to verify GDPR compliance.

        Creates a prompt that instructs the LLM to generate executable SQL queries
        that check for GDPR violations. Each assertion returns rows only when
        violations exist (empty results indicate compliance).

        Args:
            context (str):
                Retrieved GDPR documentation relevant to the schema.
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
        return dedent(
            f"""
            You are an expert GDPR compliance auditor and SQL specialist.

            Context chunks (retrieved from a {self.standard} standard vector store):
            {context}

            Task:
            Generate SQL assertions to verify {self.standard} compliance for the schema below.
            Each assertion must be a SELECT query that returns rows ONLY when violations exist.
            Empty results mean compliance.

            Focus on:
            1. Detecting personal data stored without evidence of pseudonymisation or encryption (Article 5(1)(f), Article 32)
            2. Detecting special category personal data (health, biometric, racial/ethnic origin, etc.) stored without apparent safeguards (Article 9)
            3. Verifying that tables holding personal data include columns to support the right to erasure, such as a deletion flag or erasure timestamp (Article 17)
            4. Checking for audit logging capabilities — created_at, updated_at, or equivalent timestamps — to support accountability (Article 5(2))
            5. Verifying that personal data collection appears limited to what is necessary for its purpose — flagging tables with excessive or ambiguous personal data columns (Article 5(1)(c))
            6. Identifying columns with ambiguous names that might store personal or special category data without clear justification (Article 25)

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
        Build a prompt for analyzing a failed GDPR assertion.

        Creates a prompt that helps the LLM understand why an assertion failed and
        provide specific remediation recommendations with SQL examples.

        Args:
            context (str):
                Retrieved GDPR documentation relevant to the failed assertion.
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
            You are an expert GDPR compliance auditor and database security specialist.

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
            2. STANDARD REFERENCE: Cite the exact {self.standard} Article(s) and clause(s) that apply
            3. SECURITY IMPACT: Explain the risk this violation poses to data subjects and their personal data
            4. REMEDIATION STEPS: Provide concrete, actionable steps and optionally SQL queries to fix this violation

            Your reply should:
            - Use as much wording from the given context as possible except for the REMEDIATION STEPS.
            - Be specific and actionable. If pseudonymisation or encryption is needed, specify what to apply and how.
                If personal data should be deleted to honour a right-to-erasure request, explain why and provide the SQL to do so safely. And so on.
            """
        ).strip()


if settings.USE_MOCK_COMPLIANCE_CHECKER:
    from ..utils import MockComplianceChecker

    GDPRComplianceChecker = MockComplianceChecker  # pyright: ignore[reportAssignmentType]
