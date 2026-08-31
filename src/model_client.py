from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ModelResponse:
    text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    raw: Mapping[str, Any]


class ModelClient:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.0,
        num_ctx: int = 4096,
    ) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self.base_url = (base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.turn_count = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def complete(
        self,
        messages: Iterable[Mapping[str, str]],
        tools: list[Mapping[str, Any]] | None = None,
        *,
        temperature: float | None = None,
        response_format: str | Mapping[str, Any] | None = None,
    ) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
            "stream": False,
            "options": {
                "temperature": self.temperature if temperature is None else temperature,
                "num_ctx": self.num_ctx,
            },
        }
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["format"] = response_format

        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Could not reach Ollama at {self.base_url}. Start Ollama and pull {self.model!r}."
            ) from error

        input_tokens = int(raw.get("prompt_eval_count", 0) or 0)
        output_tokens = int(raw.get("eval_count", 0) or 0)
        total_tokens = input_tokens + output_tokens
        self.turn_count += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        print(
            f"[tokens] turn={self.turn_count} input={input_tokens} "
            f"output={output_tokens} total={total_tokens}"
        )
        message = raw.get("message", {})
        text = str(message.get("content", "")).strip()
        return ModelResponse(text, input_tokens, output_tokens, total_tokens, raw)

    def stats(self, history: Iterable[Mapping[str, str]]) -> dict[str, int]:
        serialized_history = json.dumps(list(history), ensure_ascii=False, separators=(",", ":"))
        return {
            "turn_count": self.turn_count,
            "cumulative_input_tokens": self.input_tokens,
            "cumulative_output_tokens": self.output_tokens,
            "serialized_conversation_history_length": len(serialized_history),
        }

    def print_cumulative_stats(self) -> None:
        print(
            "[cumulative] "
            f"input={self.input_tokens} output={self.output_tokens} turns={self.turn_count}"
        )
