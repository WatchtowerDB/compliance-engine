#!/usr/bin/env python3

import textwrap
from pathlib import Path

from .compliance_checker import ComplianceChecker


class PCIComplianceChecker(ComplianceChecker):
    """
    PCI-DSS compliance analyzer for SQL database schemas using RAG.

    This specialized compliance checker analyzes SQL database schemas for
    compliance with the Payment Card Industry Data Security Standard (PCI-DSS).
    It uses intelligent query generation to identify potential violations related
    to cardholder data handling, encryption, access control, and logging.

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

    def __init__(
        self,
        model_path: Path | str,
        chroma_dir: Path | str,
        collection_name: str = "PCI-DSS-v4.0.1",
        retrieval_k: int = 2,
        context_window: int = 5120,  # The maximum comfortable context window we can get on an 8GB GPU with Ministral 8B
        n_gpu_layers: int = -1,
    ) -> None:
        """
        Initialize the PCI-DSS compliance checker.

        Args:
                model_path (Path | str):
                        Path to the GGUF model file for LLM inference.
                chroma_dir (Path | str):
                        Directory containing the Chroma vector database with PCI-DSS documentation.
                collection_name (str):
                        Name of the Chroma collection. Defaults to `"PCI-DSS-v4.0.1"`.
                retrieval_k (int):
                        Number of document chunks to retrieve per question.
                        Defaults to `2` (more focused retrieval for PCI-DSS specific queries).
                context_window (int):
                        Maximum context length in tokens. Defaults to `5120`
                        (the maximum comfortable size for Ministral 8B on 8GB GPU).
                n_gpu_layers (int):
                        GPU layer offloading. `-1` for all layers (recommended).
                        Defaults to `-1`.

        Note:
                The default `context_window` of `5120` is optimized for Ministral 8B on
                consumer GPUs with 8GB VRAM. Adjust based on your hardware.
        """
        super().__init__(
            model_path=model_path,
            chroma_dir=chroma_dir,
            collection_name=collection_name,
            retrieval_k=retrieval_k,
            context_window=context_window,
            n_gpu_layers=n_gpu_layers,
        )
        self.standard = "PCI-DSS v4.0.1"

    def _build_query_generation_prompt(self, schema: str) -> str:
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
                        questions as a Python list of strings. Questions are designed to work
                        well with vector store retrieval of PCI-DSS documentation.

        Note:
                The prompt explicitly asks for inference about ambiguous column names,
                as compliance issues may exist even when naming isn't explicit.
        """
        return textwrap.dedent(
            f"""
			Analyze the SQL schema and infer possible {self.standard} concerns.
			Generate ONLY 3-6 comprehensive rich questions an auditor would ask about:
			- cardholder data storage (PAN, CVV, expiration)
			- sensitive data retention
			- encryption/hashing
			- access control
			- auditing/logging
			- ambiguous columns that might contain payment data

			Infer risks even when column names are unclear.

			Keep in mind, these questions will be fed to a vector store of the {self.standard} standard to retrieve relevant context.

			Return ONLY a Python list of question strings.

			Schema:
			{schema}
			"""
        ).strip()

    def _build_prompt(self, context: str, schema: str) -> str:
        """
        Build the main PCI-DSS compliance analysis prompt.

        Constructs a comprehensive prompt that combines retrieved PCI-DSS documentation
        with the SQL schema to analyze. The prompt instructs the LLM to act as an
        expert auditor and provide structured compliance findings.

        Args:
                context (str):
                        Retrieved excerpts from PCI-DSS v4.0.1 documentation relevant
                        to the schema's compliance concerns.
                schema (str):
                        The SQL database schema to analyze for compliance.

        Returns:
                str: A formatted prompt requesting:
                        1. Compliance summary (Compliant/Non-compliant)
                        2. Specific violations with corresponding PCI-DSS clause references
                        3. Concrete remediation recommendations with SQL examples where applicable

        Note:
                The prompt explicitly asks for SQL queries in remediation suggestions,
                making the output immediately actionable for developers.
        """
        return textwrap.dedent(
            f"""
			You are an expert PCI-DSS compliance auditor and database security analyst.

			Context (from {self.standard} standard):
			{context}

			Task:
			Analyze the following SQL database schema for {self.standard} compliance.
			Identify violations and recommend concrete improvements.
			If applicable, supplement your improvements with SQL queries that would help remedy the violations.

			SQL Schema:
			{schema}

			Respond with:
			1. Compliance summary (Compliant / Non-compliant)
			2. Violations and their corresponding PCI-DSS clauses
			3. Recommended remediations
			"""
        ).strip()

    def analyze(self, schema: str) -> str:
        """
        Perform comprehensive PCI-DSS compliance analysis on a SQL schema.

        This method implements the complete RAG-based compliance checking workflow:
        1. Generate targeted compliance questions from the schema
        2. Retrieve relevant PCI-DSS documentation using those questions
        3. Analyze the schema against the retrieved context using the LLM
        4. Return a structured compliance report

        Args:
                schema (str):
                        The SQL database schema to analyze. Should be valid SQL DDL (CREATE TABLE statements, etc.).

        Returns:
                str: A detailed compliance report containing:
                        - Overall compliance verdict
                        - Specific violations with PCI-DSS clause references
                        - Actionable remediation recommendations
                        - SQL query examples for fixes (when applicable)

        Example:
                >>> checker = PCIComplianceChecker(model_path, chroma_dir)
                >>> schema = "CREATE TABLE users (id INT, cc_number VARCHAR(16));"
                >>> report = checker.analyze(schema)
                >>> print(report)
                >>> checker.close()
        """
        questions = self._generate_compliance_questions(schema)
        context = self._retrieve_context_for_questions(questions)

        # Build final analysis prompt with retrieved context
        prompt = self._build_prompt(context, schema)

        print("[INFO] Running model inference for compliance analysis...")
        response = self.llm.generate(prompt)
        print("[INFO] Analysis complete.")

        return response
