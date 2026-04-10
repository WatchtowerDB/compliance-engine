import logging
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


class LLMInference:
    """
    Handles loading and inference of Large Language Models in GGUF format.

    This class provides a high-level interface for working with quantized LLMs
    using the `llama.cpp` backend via `llama-cpp-python`. It supports both streaming
    and non-streaming generation modes, GPU acceleration, and customizable
    prompt templates.

    Attributes:
        model_path (Path):
            Path to the GGUF model file.
        prompt_template (str):
            Template string for formatting prompts. Use `{prompt}`
            as a placeholder for the actual prompt text.
        stop (str | list[str] | None):
            Stop sequences that halt generation.
        model (Llama):
            The loaded `llama.cpp` model instance.
    """

    def __init__(
        self,
        model_path: Path | str,
        context_window: int = 4096,
        n_gpu_layers: int = -1,
        prompt_template: str = "{prompt}",  # i.e., just the prompt, which is highly unlikely
        stop: str | list[str] | None = None,
    ) -> None:
        """
        Initialize the LLM inference engine with a GGUF model.

        Args:
            model_path (Path | str):
                Path to the GGUF format model file.
            context_window (int):
                Maximum context length (in tokens) the model can handle.
                Defaults to `4096`. Larger values require more memory.
            n_gpu_layers (int):
                Number of model layers to offload to GPU. Use `-1` to offload
                all layers (recommended for GPU acceleration). Use `0` for CPU-only mode.
                Defaults to `-1`.
            prompt_template (str):
                Format string for structuring prompts. Should contain
                `{prompt}` placeholder. For example, Mistral uses `"[INST] {prompt} [/INST]"`.
                Defaults to `"{prompt}"` (no formatting).
            stop (str | list[str] | None):
                Stop sequence(s) that signal the model to stop generating. Can be
                a single string or list of strings. Common examples include special
                tokens like `"[INST]"`, `"</s>"`, or custom markers. Defaults to `None`.

        Raises:
            FileNotFoundError: If the model file doesn't exist.
            ValueError: If the model file is not in valid GGUF format.
        """
        # Lazy-importing for llama-cpp to avoid it being loaded each time llm_inference.py is referenced
        from llama_cpp import Llama

        self.model_path = Path(model_path)
        self.prompt_template = prompt_template
        self.stop = stop
        self.model: Llama

        logger.info('Loading model from "%s"', self.model_path.name)
        self.model = Llama(
            model_path=str(self.model_path),
            n_gpu_layers=n_gpu_layers,
            n_ctx=context_window,
            verbose=False,
        )
        logger.info('Successfully loaded model from "%s"', self.model_path.name)

    def stream_chunks(
        self, prompt: str, max_tokens: int = 1024, temperature: float = 0.4
    ) -> Iterator:
        """
        Generate text as a stream of chunks, returning the raw iterator.

        This method is useful when you need fine-grained control over streaming
        or want to implement custom streaming handlers (e.g., for web APIs or
        real-time applications). It returns the raw `llama.cpp` iterator.

        Args:
            prompt (str):
                The input text prompt to generate from.
            max_tokens (int):
                Maximum number of tokens to generate. Note: this is a
                soft limit - generation may stop earlier due to stop sequences
                or end-of-text tokens. Defaults to `1024`.
            temperature (float):
                Sampling temperature controlling randomness. Lower values
                (e.g., `0.1`-`0.4`) produce more focused/deterministic output. Higher
                values (e.g., `0.8`-`1.0`) produce more creative/diverse output.
                Defaults to `0.4`.

        Returns:
            Iterator[CreateCompletionStreamResponse]:
                An iterator yielding completion chunks.
                Each chunk is a dictionary object containing:
                - choices[0]["text"]: The generated text token/fragment
                - choices[0]["finish_reason"]: Why generation stopped (if finished)

        Example:
            >>> llm = LLMInference("model.gguf")
            >>> for chunk in llm.stream_chunks("Hello"):
            ...     token = chunk["choices"][0]["text"]
            ...     print(token, end="", flush=True)
        """
        formatted_prompt = self.prompt_template.format(prompt=prompt)
        return self.model(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=self.stop,
            stream=True,
            echo=False,
        )  # type: ignore

    def _generate_stream(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """
        Generate text with streaming output printed to `stdout` in real-time.

        This internal method handles streaming generation with immediate console
        output, providing a typewriter effect as tokens are generated. It collects
        all tokens and returns the complete response.

        Args:
            prompt (str):
                The input text prompt to generate from.
            max_tokens (int):
                Maximum number of tokens to generate.
            temperature (float):
                Sampling temperature for generation randomness.

        Returns:
            str: The complete generated text, with leading/trailing whitespace removed.

        Note:
            This method prints to stdout as generation occurs. Use `generate()` with
            `stream=False` if you need silent generation.
        """
        response_tokens = []
        print()

        for chunk in self.stream_chunks(prompt, max_tokens, temperature):
            token = chunk["choices"][0]["text"]  # type: ignore (chunk can be str or something else if stream is False, but it isn't)
            print(token, end="", flush=True)
            response_tokens.append(token)

        print("\n")
        return "".join(response_tokens).strip()

    def _generate_non_stream(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> str:
        """
        Generate text without streaming, returning the complete response at once.

        This internal method performs generation silently (no console output) and
        returns only when generation is complete. Useful for batch processing or
        when you don't need real-time feedback.

        Args:
            prompt (str):
                The input text prompt to generate from.
            max_tokens (int):
                Maximum number of tokens to generate.
            temperature (float):
                Sampling temperature for generation randomness.

        Returns:
            str: The complete generated text, with leading/trailing whitespace removed.

        Note:
            No output is printed during generation. This is faster than streaming
            for small generations.
        """
        formatted_prompt = self.prompt_template.format(prompt=prompt)
        output = self.model(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=self.stop,
            stream=False,
            echo=False,
        )
        return output["choices"][0]["text"].strip()  # type: ignore

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.4,
        stream: bool = True,
    ) -> str:
        """
        Generate text from a prompt with configurable streaming behavior.

        This is the main public interface for text generation. It automatically
        routes to the appropriate internal method based on the streaming preference.

        Args:
            prompt (str):
                The input text prompt to generate from. Will be formatted using
                the `prompt_template` specified during initialization.
            max_tokens (int):
                Maximum number of tokens to generate. Defaults to `1024`.
            temperature (float):
                Controls randomness in generation. Range is typically `0.0`-`2.0`.
                - `0.0`-`0.3`: Very focused, deterministic (good for factual tasks)
                - `0.4`-`0.7`: Balanced creativity and coherence (default range)
                - `0.8`-`1.0`: More creative and diverse
                - `1.0`+: Very random (rarely useful)
                Defaults to `0.4`.
            stream (bool):
                Whether to stream output to `stdout` as it's generated.
                - `True`: Displays real-time generation (typewriter effect)
                - `False`: Silent generation, returns complete text at end
                Defaults to `True`.

        Returns:
            str: The complete generated text response, stripped of leading/trailing
                 whitespace.

        Example:
            >>> llm = LLMInference("model.gguf", prompt_template="[INST] {prompt} [/INST]")
            >>> response = llm.generate("Explain quantum computing", max_tokens=500)
            >>> print(response)
        """
        if stream:
            return self._generate_stream(prompt, max_tokens, temperature)
        else:
            return self._generate_non_stream(prompt, max_tokens, temperature)

    def close(self):
        """
        Clean up model resources and free memory.

        Attempts to properly close the `llama.cpp` model instance and release
        associated resources (GPU memory, etc.). Should be called when the
        model is no longer needed.

        This method is safe to call multiple times and suppresses any exceptions
        that occur during cleanup.

        Example:
            >>> llm = LLMInference("model.gguf")
            >>> try:
            ...     response = llm.generate("Hello")
            ... finally:
            ...     llm.close()	# Ensure cleanup happens
        """
        if self.model is not None:
            try:
                self.model.close()
            except Exception:
                pass
