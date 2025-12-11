#!/usr/bin/env python3

import json
from abc import ABC, abstractmethod
from pathlib import Path

from .context_retriever import ContextRetriever
from .llm_inference import LLMInference


class ComplianceChecker(ABC):
	"""
	Abstract base class for RAG-powered compliance analysis systems.

	This class provides a framework for building compliance checkers that use
	Retrieval Augmented Generation (RAG) to analyze schemas, configurations, or
	other artifacts against specific compliance standards (PCI-DSS, HIPAA, GDPR, etc.).

	The workflow:
	1. Generate targeted compliance questions from the artifact being analyzed
	2. Use vector search to retrieve relevant standard documentation
	3. Perform LLM-powered analysis using the retrieved context

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
		prompt_template: str = "[INST] {prompt} [/INST]",	# The ministral template
		stop: str | list[str] | None = ["[INST]", "[/INST]"]	# The ministral stops
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
			retrieval_k=retrieval_k
		)
		self.llm = LLMInference(
			model_path=model_path,
			context_window=context_window,
			n_gpu_layers=n_gpu_layers,
			prompt_template=prompt_template,
			stop=stop
		)

	@abstractmethod
	def _build_query_generation_prompt(self, schema: str) -> str:
		"""
		Construct a prompt for generating compliance-specific questions.

		This method should create a prompt that instructs the LLM to analyze the
		input (schema, config, etc.) and generate targeted questions that will be
		used to retrieve relevant compliance documentation.

		Args:
			schema (str):
				The artifact to analyze (SQL schema, config file, etc.).

		Returns:
			str: A prompt instructing the LLM to generate compliance questions.

		Note:
			Subclasses should instruct the model to return a Python list of strings.
		"""
		pass

	@abstractmethod
	def _build_prompt(self, context: str, schema: str) -> str:
		"""
		Construct the main compliance analysis prompt.

		This method should create a comprehensive prompt that includes:
		- The retrieved context from compliance documentation
		- The artifact being analyzed
		- Specific instructions for compliance assessment
		- Expected output format

		Args:
			context (str):
				Retrieved compliance documentation relevant to the artifact.
			schema (str):
				The artifact to analyze (SQL schema, config file, etc.).

		Returns:
			str: A complete prompt for compliance analysis.
		"""
		pass

	@abstractmethod
	def analyze(self, schema: str) -> str:
		"""
		Perform compliance analysis on the given artifact.

		This is the main entry point for compliance checking. Subclasses should
		implement the full analysis workflow:
		1. Generate compliance questions
		2. Retrieve relevant documentation
		3. Perform analysis with the LLM
		4. Return formatted results

		Args:
			schema (str):
				The artifact to analyze (SQL schema, config, policy, etc.).

		Returns:
			str: A formatted compliance analysis report.
		"""
		pass

	def _generate_compliance_questions(self, schema: str) -> list[str]:
		"""
		Generate targeted compliance questions from the artifact using the LLM.

		This method uses the LLM to intelligently extract compliance concerns from
		the input artifact. The generated questions are then used to query the
		vector store for relevant documentation, making retrieval more focused
		than direct schema-based queries.

		Args:
			schema (str):
				The artifact to analyze (SQL schema, configuration, etc.).

		Returns:
			list[str]: A list of compliance question strings. Returns up to 6 questions,
				even if JSON parsing fails (fallback to text extraction).

		Raises:
			No exceptions are raised - parsing failures trigger fallback logic.

		Note:
			The method expects JSON output from the LLM but has robust fallback
			handling for malformed responses, including stripping markdown code blocks.
		"""
		print("[INFO] Generating compliance questions from schema...")
		prompt = self._build_query_generation_prompt(schema)

		# Use lower temperature for more consistent, focused question generation
		response = self.llm.generate(
			prompt, 
			max_tokens=1024, 
			temperature=0.3,
			stream=False
		)

		# Parse JSON response
		try:
			# Clean up potential markdown formatting
			cleaned_response = response.strip()
			if cleaned_response.startswith("```python3"):
				cleaned_response = cleaned_response[10:]
			if cleaned_response.startswith("```python"):
				cleaned_response = cleaned_response[9:]
			if cleaned_response.startswith("```py"):
				cleaned_response = cleaned_response[5:]
			if cleaned_response.startswith("```"):
				cleaned_response = cleaned_response[3:]
			if cleaned_response.endswith("```"):
				cleaned_response = cleaned_response[:-3]
			cleaned_response = cleaned_response.strip()

			questions = json.loads(cleaned_response)

			if not isinstance(questions, list):
				raise ValueError("[ERROR] Compliance questions response is not a list.")

			print(f"[INFO] Generated {len(questions)} compliance questions.")
			return questions

		except (json.JSONDecodeError, ValueError) as e:
			print(f"[WARNING] Failed to parse questions as JSON: {e}")
			print(f"[WARNING] Raw response: {response}")

			# Fallback: try to extract questions from text
			lines = response.strip().split('\n')
			questions = [
				line.strip(' -"[]\'') 
				for line in lines 
				if line.strip() and len(line.strip()) > 10
			]
			print(f"[INFO] Extracted {len(questions)} questions from text.")
			return questions[:6]	# Limit to 6 questions

	def _retrieve_context_for_questions(self, questions: list[str]) -> str:
		"""
		Retrieve relevant compliance documentation for multiple questions.

		This method queries the vector store with each generated question and
		combines all retrieved contexts into a single comprehensive context string.
		Uses a set to automatically deduplicate retrieved document chunks.

		Args:
			questions (list[str]):
				List of compliance-related questions to search for.

		Returns:
			str: Combined context from all retrievals, with double-newline separators
				between unique document chunks.
		"""
		print(f"[INFO] Retrieving context for {len(questions)} questions...")
		all_contexts = set()	# Using sets for automatic de-duplication of contexts

		for i, question in enumerate(questions, 1):
			print(f"[INFO] Retrieving context for question {i}/{len(questions)}")
			for context in self.context_retriever.context(question):
				all_contexts.add(context.page_content)

		combined_context = "\n\n".join(all_contexts)
		print(f"[INFO] Retrieved and combined all contexts.")
		return combined_context

	def close(self):
		"""
		Clean up resources used by the compliance checker.

		Releases LLM model resources and frees associated memory (GPU/CPU).
		Should be called when the compliance checker is no longer needed.

		Example:
			>>> checker = PCIComplianceChecker(model_path, chroma_dir)
			>>> try:
			... 	result = checker.analyze(schema)
			... finally:
			... 	checker.close()
		"""
		self.llm.close()
