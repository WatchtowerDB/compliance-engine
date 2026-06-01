import logging
import threading
from enum import Enum
from pathlib import Path
from queue import Queue
from typing import Iterator

logger = logging.getLogger(__name__)


class PoolState(str, Enum):
    """
    Represents the initialization state of an `LLMInferencePool`.

    States:
        NOT_INITIALIZED:
            Pool has been created but loading has not started.

        INITIALIZING:
            Pool instances are currently being loaded in a background thread.

        INITIALIZED:
            All model instances loaded successfully.

        PARTIAL:
            Some instances loaded successfully while others failed.

        ERROR:
            All instances failed to load and the pool is unusable.
    """

    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    PARTIAL = "partial"
    ERROR = "error"


class LLMInference:
    """
    Single model instance. Never instantiate directly, use `LLMInferencePool`.

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
        context_window: int = 8192,
        n_gpu_layers: int = -1,
        prompt_template: str = "{prompt}",  # i.e., just the prompt, which is highly unlikely
        stop: str | list[str] | None = None,
        top_k: int = 40,
        fa: bool = False,
        swa_full: bool | None = None,
    ) -> None:
        """
        Initialize the LLM inference engine with a GGUF model.

        Args:
            model_path (Path | str):
                Path to the GGUF format model file.
            context_window (int):
                Maximum context length (in tokens) the model can handle.
                Defaults to `8192`. Larger values require more memory.
            n_gpu_layers (int):
                Number of model layers to offload to GPU. Use `-1` to offload
                all layers (recommended for GPU acceleration). Use `0` for CPU-only mode.
                Defaults to `-1`.
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
                Higher values increase diversity but may reduce coherence. Defaults to `40`.
            fa (bool):
                Whether to use flash attention (if supported by the model and hardware). Defaults to `False`.
            swa_full (bool | None):
                Whether to use SWA-Full attention (if supported by the model and hardware).
                Defaults to `None`, and leave it like that if you don't know what it is.

        Raises:
            FileNotFoundError: If the model file doesn't exist.
            ValueError: If the model file is not in valid GGUF format.
        """
        # Lazy-importing for llama-cpp to avoid it being loaded each time llm_inference.py is referenced
        from llama_cpp import Llama

        self.model_path = Path(model_path)
        self.context_window = context_window
        self.n_gpu_layers = n_gpu_layers
        self.prompt_template = prompt_template
        self.stop = stop
        self.top_k = top_k
        self.fa = fa
        self.swa_full = swa_full

        logger.info('Loading model from "%s"', self.model_path.name)
        self.model = Llama(
            model_path=str(self.model_path),
            n_gpu_layers=self.n_gpu_layers,
            n_ctx=self.context_window,
            flash_attn=self.fa,
            swa_full=self.swa_full,
            verbose=False,
        )
        logger.info('Successfully loaded model from "%s"', self.model_path.name)

    @property
    def settings(self) -> dict:
        """
        Get the current model settings as a dictionary. Not writable.

        This property provides a convenient way to access the model's configuration
        parameters, which can be useful for debugging, logging, or passing settings
        to other components.

        Returns:
            dict: A dictionary containing the model's configuration settings.
        """
        return {
            "model_path": str(self.model_path),
            "context_window": self.context_window,
            "n_gpu_layers": self.n_gpu_layers,
            "prompt_template": self.prompt_template,
            "stop": self.stop,
            "top_k": self.top_k,
            "fa": self.fa,
            "swa_full": self.swa_full,
        }

    def stream_chunks(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.4
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
                or end-of-text tokens. Defaults to `2048`.
            temperature (float):
                Sampling temperature controlling randomness. Lower values
                (e.g., `0.1`-`0.4`) produce more focused/deterministic output. Higher
                values (e.g., `0.8`-`1.0`) produce more creative/diverse output.
                Defaults to `0.4`.

        Returns:
            Iterator[CreateCompletionStreamResponse]: # NOT SURE ABOUT THE RETURN TYPE. IT'S A YIELD
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
        yield from self.model(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=self.stop,
            top_k=self.top_k,
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
            top_k=self.top_k,
            stream=False,
            echo=False,
        )
        return output["choices"][0]["text"].strip()  # type: ignore

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
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
                Maximum number of tokens to generate. Defaults to `2048`.
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

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a string using the model's native tokenizer.

        This is useful for ensuring inputs stay within a model's `context_window`.

        Args:
            text (str): The text to count tokens for.

        Returns:
            int: The token count.
        """
        if not text:
            return 0

        return len(self.model.tokenize(text.encode("utf-8"), add_bos=False))

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


class LLMInferencePool:
    """
    Fixed-size pool of LLMInference instances for a single model file.

    Construction is non-blocking; instances are loaded in a background thread
    and the pool state transitions as loading progresses. Callers that try to
    `acquire()` while the pool is still initializing will block at `Queue.get()`
    until at least one instance is ready.

    State transitions:

                                       → INITIALIZED
        NOT_INITIALIZED → INITIALIZING → PARTIAL (some failed)
                                       → ERROR   (all failed)
    """

    _pools: dict[str, "LLMInferencePool"] = {}
    _registry_lock = threading.Lock()

    def __init__(self, model_path: Path | str, pool_size: int, **kwargs) -> None:
        """
        Initialize an empty inference pool for a specific model.

        The pool is created in a non-loaded state. Call `load()` to begin
        asynchronously loading model instances into the pool.

        Args:
            model_path (Path | str):
                Path to the GGUF model file associated with this pool.

            pool_size (int):
                Number of `LLMInference` instances to maintain in the pool.

            **kwargs:
                Additional keyword arguments forwarded directly to
                `LLMInference` during instance construction.

        Note:
            Construction itself does not load any models. Loading is deferred
            until `load()` is called.
        """
        self._queue: Queue[LLMInference] = Queue()
        self._pool_size = pool_size
        self._loaded = 0
        self._failed = 0
        self._state = PoolState.NOT_INITIALIZED
        self._state_lock = threading.Lock()
        self._kwargs = kwargs
        self._model_path = Path(model_path)
        self._failed_frameworks: list[str] = []

    @classmethod
    def for_model(
        cls, model_path: Path | str, pool_size: int = 1, **kwargs
    ) -> "LLMInferencePool":
        """
        Retrieve or create a shared pool for a model path.

        This method implements a registry-based singleton pattern where each
        unique model path maps to exactly one `LLMInferencePool` instance.

        If a pool already exists for the given model path, the existing pool
        is returned and any new configuration arguments are ignored.

        Args:
            model_path (Path | str):
                Path to the GGUF model file.

            pool_size (int):
                Desired number of pooled model instances when creating
                a new pool. Ignored if the pool already exists.
                Defaults to `1`.

            **kwargs:
                Additional keyword arguments forwarded to the pool constructor
                when creating a new pool. Ignored if the pool already exists.

        Returns:
            LLMInferencePool:
                The existing or newly created pool associated with the model path.

        Warns:
            Logs a warning if the pool already exists and the provided
            configuration differs from the existing configuration.

        Note:
            This method does not automatically start model loading.
            Call `load()` explicitly after retrieving the pool.
        """
        key = str(Path(model_path))

        with cls._registry_lock:
            if key not in cls._pools:
                cls._pools[key] = cls(
                    model_path,
                    pool_size=pool_size,
                    **kwargs,
                )
            else:
                existing = cls._pools[key]

                if existing._pool_size != pool_size or existing._kwargs != kwargs:
                    logger.warning(
                        "Pool for %s already exists; ignoring new configuration. "
                        "Existing: pool_size=%s kwargs=%s | "
                        "Requested: pool_size=%s kwargs=%s",
                        key,
                        existing._pool_size,
                        existing._kwargs,
                        pool_size,
                        kwargs,
                    )

            return cls._pools[key]

    @classmethod
    def get(cls, model_path: Path | str) -> "LLMInferencePool | None":
        """
        Retrieve an existing pool without creating one.

        Args:
            model_path (Path | str):
                Path to the GGUF model file.

        Returns:
            LLMInferencePool | None:
                The existing pool associated with the model path,
                or `None` if no pool has been registered.
        """
        return cls._pools.get(str(Path(model_path)))

    def _load_all(self) -> None:
        """
        Load all model instances into the pool.

        This internal worker method is executed in a background thread
        created by `load()`.

        For each requested pool slot:
            - Attempts to construct an `LLMInference` instance.
            - Inserts successful instances into the queue.
            - Tracks failures and updates pool statistics.

        Once loading completes, the pool state is updated to one of:
            - `INITIALIZED`
            - `PARTIAL`
            - `ERROR`

        Note:
            Exceptions raised during individual instance construction are
            caught and logged so that remaining instances can continue loading.
        """
        logger.debug("Loading all instances for %s", self._model_path.name)
        for _ in range(self._pool_size):
            try:
                instance = LLMInference(self._model_path, **self._kwargs)
                self._queue.put(instance)
                with self._state_lock:
                    self._loaded += 1
            except Exception:
                logger.exception(
                    "Failed to load LLMInference instance for %s", self._model_path
                )
                with self._state_lock:
                    self._failed += 1

        with self._state_lock:
            if self._loaded == 0:
                self._state = PoolState.ERROR
            elif self._failed > 0:
                self._state = PoolState.PARTIAL
            else:
                self._state = PoolState.INITIALIZED

        logger.info(
            "Pool for %s: state=%s loaded=%s failed=%s",
            self._model_path.name,
            self._state,
            self._loaded,
            self._failed,
        )

    def load(self) -> None:
        """
        Begin asynchronously loading model instances into the pool.

        This method spawns a daemon thread that constructs all
        `LLMInference` instances and inserts them into the internal queue.

        The method returns immediately and does not block while models load.

        Pool state transitions automatically as loading progresses:

            NOT_INITIALIZED -> INITIALIZING
                            -> INITIALIZED
                            -> PARTIAL
                            -> ERROR

        Subsequent calls after initialization has started are ignored.

        Note:
            Callers can monitor loading progress through:
            - `state`
            - `loaded_count`
            - `failed_count`
        """
        with self._state_lock:
            if self._state != PoolState.NOT_INITIALIZED:
                logger.debug(
                    "Pool for %s is already loading or loaded", self._model_path.name
                )
                return

            logger.debug(
                "Starting to load pool for %s with size %s",
                self._model_path.name,
                self._pool_size,
            )
            self._state = PoolState.INITIALIZING

        thread = threading.Thread(target=self._load_all, daemon=True)
        thread.start()

    @property
    def state(self) -> PoolState:
        """
        Get the current state of the pool.

        Returns:
            PoolState:
                The current lifecycle state of the pool.
        """
        with self._state_lock:
            return self._state

    @property
    def loaded_count(self) -> int:
        """
        Get the number of successfully loaded model instances.

        Returns:
            int:
                Number of successfully initialized `LLMInference` objects.
        """
        with self._state_lock:
            return self._loaded

    @property
    def failed_count(self) -> int:
        """
        Get the number of model instances that failed to load.

        Returns:
            int:
                Number of failed `LLMInference` initializations.
        """
        with self._state_lock:
            return self._failed

    def acquire(self) -> "LLMInferenceContext":
        """
        Acquire an inference instance from the pool.

        This method returns a context manager that safely checks out
        an `LLMInference` instance from the internal queue and automatically
        returns it when the context exits.

        The operation blocks if no instances are currently available.

        Returns:
            LLMInferenceContext:
                Context manager providing exclusive temporary access
                to a pooled `LLMInference` instance.

        Raises:
            RuntimeError:
                If the pool is in `ERROR` state and no instances are available.

        Example:
            >>> with pool.acquire() as llm:
            ...     response = llm.generate("Hello")
        """
        if self._state == PoolState.ERROR and self._queue.empty():
            raise RuntimeError(
                f"LLMInferencePool for {self._model_path} is in ERROR state; "
                "no instances available."
            )

        return LLMInferenceContext(self._queue)


class LLMInferenceContext:
    """
    Context manager for safely borrowing pooled inference instances.

    Instances of this class are returned by `LLMInferencePool.acquire()`.

    On entering the context:
        - An `LLMInference` instance is removed from the queue.

    On exiting the context:
        - The instance is automatically returned to the queue.

    This guarantees safe resource return even if exceptions occur
    during inference.
    """

    def __init__(self, queue: Queue[LLMInference]) -> None:
        """
        Initialize the inference context manager.

        Args:
            queue (Queue[LLMInference]):
                Queue containing available pooled inference instances.
        """
        self._queue: Queue[LLMInference] = queue
        self._instance: LLMInference | None = None

    def __enter__(self) -> LLMInference:
        """
        Acquire an inference instance from the queue.

        This method blocks until an instance becomes available.

        Returns:
            LLMInference:
                A checked-out inference instance for temporary exclusive use.
        """
        instance = self._queue.get()
        self._instance = instance
        return instance

    def __exit__(self, *_) -> None:
        """
        Return the checked-out inference instance to the pool.

        This method is automatically invoked when exiting the `with`
        statement, even if an exception occurs inside the context.

        Args:
            *_:
                Standard context manager exception arguments
                (`exc_type`, `exc_value`, `traceback`), ignored here.
        """
        if self._instance is not None:
            self._queue.put(self._instance)
            self._instance = None
