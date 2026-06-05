import json
import logging
from enum import Enum
from typing import Iterator

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

# Module-level persistent client; one connection pool for the entire process.
# All checkers share this client; the server handles concurrency.
# Read timeout is long because LLM generation can be slow.
_http_client = httpx.Client(
    base_url=settings.LLM_SERVER_URL,
    timeout=httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=None),
)


class LLMInference:
    """HTTP client wrapper around the llama inference server."""

    class ServerStatus(Enum):
        """
        Namespace for inference server status string constants.

        The llama-server communicates readiness through HTTP status codes.
        These constants normalize that into strings suitable for API responses
        and SSE event payloads.
        """

        NOT_INITIALIZED = "not_initialized"  # server not reachable
        INITIALIZING = "initializing"  # server up, model still loading (HTTP 503)
        INITIALIZED = "initialized"  # server ready (HTTP 200)
        ERROR = "error"  # unexpected response or exception

    def __init__(
        self,
        prompt_template: str = "{prompt}",  # i.e., just the prompt, which is highly unlikely
        stop: str | list[str] | None = None,
        top_k: int = 64,
    ) -> None:
        """
        Initialize the LLM inference client.

        Args:
            prompt_template (str):
                Format string for structuring prompts. Should contain
                `{prompt}` placeholder. For example, Mistral uses `"[INST] {prompt} [/INST]"`.
                Defaults to `"{prompt}"` (no formatting).

                It's worth noting that this way of formatting prompts, while is the most flexible,
                is not necessarily the most efficient/robust one. Each model may have its own
                inference library/api that provides better interfaces for model-specific settings.

                If the project decides to commit to a single model, this way of formatting prompts
                should be replaced with the model's native way.
            stop (str | list[str] | None):
                Stop sequence(s) that signal the model to stop generating. Can be
                a single string or list of strings. Common examples include special
                tokens like `"[INST]"`, `"</s>"`, or custom markers. Defaults to `None`.
            top_k (int):
                The number of highest probability tokens to keep for top-k sampling.
                Higher values increase diversity but may reduce coherence. Defaults to `64`.
        """
        self.prompt_template = prompt_template
        self.stop: list[str] = (
            [stop] if isinstance(stop, str) else (list(stop) if stop else [])
        )
        self.top_k = top_k

    def stream_chunks(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.4
    ) -> Iterator[dict]:
        """
        Stream completion chunks from the inference server.

        Yields dicts that match the shape of `llama_cpp`'s
        `CreateCompletionStreamResponse` so all callers remain unchanged:

        >>> chunk["choices"][0]["text"]             # generated token
        >>> chunk["choices"][0]["finish_reason"]    # None until done

        Args:
            prompt (str):
                The input text prompt to generate from.
            max_tokens (int):
                Maximum number of tokens to generate. Defaults to `2048`.
            temperature (float):
                Sampling temperature. Lower values produce more focused
                output; higher values produce more diverse output.
                Defaults to `0.4`.

        Yields:
            dict: Completion chunk with `choices[0]["text"]` and
                `choices[0]["finish_reason"]`.

        Raises:
            httpx.HTTPStatusError: If the server returns a non-2xx response.
            httpx.TimeoutException: If the server does not respond in time.
        """
        formatted_prompt = self.prompt_template.format(prompt=prompt)

        with _http_client.stream(
            "POST",
            "/v1/completions",
            timeout=httpx.Timeout(connect=30.0, read=None, write=30.0, pool=None),
            json={
                "prompt": formatted_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stop": self.stop,
                "top_k": self.top_k,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    yield {
                        "choices": [
                            {
                                "text": payload["choices"][0].get("text", ""),
                                "finish_reason": payload["choices"][0].get(
                                    "finish_reason"
                                ),
                            }
                        ]
                    }

    def _generate_stream(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """
        Generate text via the server with streaming output printed to stdout.

        Collects all tokens as they arrive and returns the complete response.
        Primarily useful for CLI and test contexts.

        Args:
            prompt (str): The input text prompt.
            max_tokens (int): Maximum tokens to generate.
            temperature (float): Sampling temperature.

        Returns:
            str: The complete generated text, stripped of leading/trailing whitespace.
        """
        response_tokens = []
        print()

        for chunk in self.stream_chunks(prompt, max_tokens, temperature):
            token = chunk["choices"][0]["text"]
            print(token, end="", flush=True)
            response_tokens.append(token)

        print("\n")
        return "".join(response_tokens).strip()

    def _generate_non_stream(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> str:
        """
        Generate text via the server without streaming.

        Returns only when generation is complete. No output is printed
        during generation. Useful for batch processing or when you don't
        need real-time feedback.

        Args:
            prompt (str): The input text prompt.
            max_tokens (int): Maximum tokens to generate.
            temperature (float): Sampling temperature.

        Returns:
            str: The complete generated text, stripped of leading/trailing whitespace.

        Raises:
            httpx.HTTPStatusError: If the server returns a non-2xx response.
        """
        formatted_prompt = self.prompt_template.format(prompt=prompt)
        response = _http_client.post(
            "/v1/completions",
            json={
                "prompt": formatted_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stop": self.stop,
                "top_k": self.top_k,
                "stream": False,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["text"].strip()

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.4,
        stream: bool = True,
    ) -> str:
        """
        Generate text from a prompt with configurable streaming behavior.

        This is the main public interface for text generation. It routes
        to the appropriate internal method based on the streaming preference.

        Args:
            prompt (str):
                The input text prompt to generate from. Will be formatted
                using `prompt_template` before being sent to the server.
            max_tokens (int):
                Maximum number of tokens to generate. Defaults to `2048`.
            temperature (float):
                Controls randomness in generation. Range is typically `0.0`–`2.0`. Defaults to `0.4`.
            stream (bool):
                Whether to stream output to stdout as it is generated.

                - `True`: Displays real-time generation (typewriter effect)
                - `False`: Silent generation, returns complete text at end

                Defaults to `True`.

        Returns:
            str: The complete generated text response, stripped of leading/trailing whitespace.

        Example:
            >>> llm = LLMInference(prompt_template="[INST] {prompt} [/INST]")
            >>> response = llm.generate("Explain quantum computing", max_tokens=500)
            >>> print(response)
        """
        if stream:
            return self._generate_stream(prompt, max_tokens, temperature)
        return self._generate_non_stream(prompt, max_tokens, temperature)

    def count_tokens(self, text: str) -> int:
        """
        Approximate the token count for a string via the server's tokenize endpoint.

        Falls back to a character-based estimate (~4 chars per token) if the
        endpoint is unavailable or returns an unexpected response.

        Args:
            text (str): The text to count tokens for.

        Returns:
            int: The token count, or an approximation on failure.
        """
        if not text:
            return 0

        try:
            response = _http_client.post("/tokenize", json={"content": text})
            response.raise_for_status()
            return len(response.json().get("tokens", []))
        except Exception:
            logger.warning(
                "Tokenize endpoint unavailable; falling back to character estimate"
            )
            return len(text) // 4

    def health(self) -> dict:
        """
        Query the llama-server `/health` endpoint and return a normalized
        status dict.

        The native llama-server communicates readiness through HTTP status codes:

        - `200`: server and model are ready → `initialized`
        - `503`: server is up but model is still loading → `initializing`
        - `ConnectError`: server is not running → `not_initialized`
        - Anything else → `error`

        Returns:
            dict: A dict with at minimum a `status` key (one of
                `ServerStatus` constants) and optionally a `detail` key
                with the raw server response body or error description.
        """
        try:
            response = _http_client.get("/health", timeout=5.0)
            if response.status_code == 200:
                return {
                    "status": self.ServerStatus.INITIALIZED,
                    "detail": response.json(),
                }
            if response.status_code == 503:
                return {
                    "status": self.ServerStatus.INITIALIZING,
                    "detail": response.json(),
                }
            return {
                "status": self.ServerStatus.ERROR,
                "detail": {"error": f"Unexpected status {response.status_code}"},
            }
        except httpx.ConnectError:
            return {
                "status": self.ServerStatus.NOT_INITIALIZED,
                "detail": {"error": "Inference server unreachable."},
            }
        except Exception as e:
            return {"status": self.ServerStatus.ERROR, "detail": {"error": str(e)}}

    def close(self) -> None:
        """
        No-op. The inference server manages its own model lifecycle.

        Retained for API compatibility with the old in-process backend.
        Call `_http_client.close()` at process shutdown if explicit
        connection cleanup is needed.

        TODO: Remove instances of this method from code, if any, and check
        if resources are being properly cleaned up, or if a proper cleanup
        mechanism is needed.
        """
        pass
