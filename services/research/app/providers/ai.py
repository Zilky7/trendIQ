"""OpenAI-compatible AI client with a fail-closed configuration boundary."""

from __future__ import annotations

import json
import os
from typing import Any, Mapping

import httpx


SYSTEM_PROMPT = """You explain only the supplied technical facts and timestamped event evidence.
Do not invent news, causal claims, prices, links, dates, or trade levels.
Return JSON with summary, reasoning_steps, risks, and execution_plan.
Every summary, reasoning_steps item, and risks item must be copied verbatim
from the supplied facts. Copy execution_plan exactly from the supplied facts."""

_TIMEOUT_SECONDS = 20.0


class AIClient:
    """Call Chat Completions only when every required setting is present.

    A provider failure intentionally returns ``None`` so callers can use the
    deterministic report instead of emitting an ungrounded partial response.
    """

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._base_url = os.getenv("AI_BASE_URL", "").rstrip("/")
        self._api_key = os.getenv("AI_API_KEY", "")
        self._model = os.getenv("AI_MODEL", "")
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self._base_url and self._api_key and self._model)

    def generate(self, facts: Mapping[str, Any]) -> dict[str, Any] | None:
        """Return provider JSON, or ``None`` on config, timeout, or API errors."""
        if not self.configured:
            return None

        request_body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Supplied facts only:\n" + json.dumps(facts, ensure_ascii=False),
                },
            ],
        }
        try:
            with httpx.Client(timeout=_TIMEOUT_SECONDS, transport=self._transport) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=request_body,
                )
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else None
        except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
