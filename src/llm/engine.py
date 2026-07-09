from __future__ import annotations

import sys
import time
from typing import Optional, Generator
from pathlib import Path

from src.config.config import Config


class LLMEngine:
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self._loaded = False
        self._load_time = 0.0
        self._tokens_generated = 0
        self._generation_start = 0.0

    def load(self) -> None:
        if self._loaded:
            return

        model_path = Path(self.config.model.path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_path}. "
                "Use the download script or update model.path in config."
            )

        start = time.time()

        try:
            from llama_cpp import Llama
        except ImportError:
            print(
                "Error: llama-cpp-python is not installed.\n"
                "Install it with: pip install llama-cpp-python",
                file=sys.stderr,
            )
            sys.exit(1)

        kwargs = {
            "model_path": str(model_path),
            "n_ctx": self.config.model.context_size,
            "n_gpu_layers": self.config.model.n_gpu_layers,
            "verbose": self.config.model.verbose,
            "n_threads": self.config.model.n_threads,
        }

        self.model = Llama(**kwargs)
        self._load_time = time.time() - start
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_time(self) -> float:
        return self._load_time

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        repeat_penalty: Optional[float] = None,
        stop: Optional[list[str]] = None,
        stream: bool = True,
    ) -> Generator[str, None, None]:
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        temperature = temperature if temperature is not None else self.config.model.temperature
        max_tokens = max_tokens if max_tokens is not None else self.config.model.max_tokens
        top_p = top_p if top_p is not None else self.config.model.top_p
        repeat_penalty = repeat_penalty if repeat_penalty is not None else self.config.model.repeat_penalty
        stop = stop or []

        self._tokens_generated = 0
        self._generation_start = time.time()

        response = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
            stop=stop,
            stream=stream,
        )

        for chunk in response:
            if "choices" in chunk and len(chunk["choices"]) > 0:
                delta = chunk["choices"][0].get("text", "")
                if delta:
                    self._tokens_generated += 1
                    yield delta

    @property
    def tokens_per_second(self) -> float:
        elapsed = time.time() - self._generation_start
        if elapsed <= 0:
            return 0.0
        return self._tokens_generated / elapsed

    @property
    def tokens_generated(self) -> int:
        return self._tokens_generated

    def unload(self) -> None:
        if self.model is not None:
            self.model.close()
            self.model = None
            self._loaded = False
