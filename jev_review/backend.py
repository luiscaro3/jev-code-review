"""Small, validated TypeSafe Jev HTTP client."""

from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from .types import Decision


class BackendError(RuntimeError):
    pass


class JevBackend:
    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        timeout_seconds: float,
        max_retries: int,
        api_key: str | None = None,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.api_key = (
            api_key or os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY")
        )
        self.opener = opener or urllib.request.urlopen
        if not self.api_key:
            raise BackendError("Set TYPESAFE_API_KEY (or JEV_API_KEY) before running a review.")

    def decide(
        self, state: str, questions: dict[str, dict[str, Any]]
    ) -> tuple[dict[str, Decision], dict[str, Any]]:
        payload = {"state": state, "model": self.model, "questions": questions}
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        response: dict[str, Any] | None = None
        for attempt in range(self.max_retries + 1):
            request = urllib.request.Request(
                self.endpoint,
                data=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "jev-code-review/0.1.0",
                },
                method="POST",
            )
            try:
                with self.opener(request, timeout=self.timeout_seconds) as opened:
                    response = json.load(opened)
                break
            except urllib.error.HTTPError as error:
                retryable = error.code in {429, 500, 502, 503, 504}
                if not retryable or attempt == self.max_retries:
                    detail = error.read().decode("utf-8", errors="replace")[:500]
                    raise BackendError(f"TypeSafe API HTTP {error.code}: {detail}") from error
            except (urllib.error.URLError, TimeoutError) as error:
                if attempt == self.max_retries:
                    raise BackendError(f"TypeSafe API request failed: {error}") from error
            time.sleep(min(2**attempt, 8))
        if response is None:
            raise BackendError("TypeSafe API returned no response")
        return self._validate(response, questions)

    @staticmethod
    def _validate(
        response: dict[str, Any], questions: dict[str, dict[str, Any]]
    ) -> tuple[dict[str, Decision], dict[str, Any]]:
        try:
            answers = response["answers"]
            resolved_model = response["model"]
            usage = response.get("usage", {})
            if not isinstance(answers, dict) or not isinstance(resolved_model, str):
                raise ValueError("invalid response envelope")
            if set(answers) != set(questions):
                raise ValueError("answer names do not match requested questions")
            decisions: dict[str, Decision] = {}
            for name, specification in questions.items():
                answer = answers[name]
                if answer.get("type") != "choice":
                    raise ValueError(f"{name}: wrong answer type")
                choices = set(specification["criteria"])
                choice = answer["choice"]
                probabilities = answer["probabilities"]
                confidence = answer["confidence"]
                if choice not in choices or set(probabilities) != choices:
                    raise ValueError(f"{name}: invalid choices")
                normalized: dict[str, float] = {}
                for label, value in probabilities.items():
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        raise ValueError(f"{name}: invalid probability")
                    if not math.isfinite(value) or not 0 <= value <= 1:
                        raise ValueError(f"{name}: invalid probability")
                    normalized[label] = float(value)
                if abs(sum(normalized.values()) - 1) > 0.05:
                    raise ValueError(f"{name}: probabilities do not sum to one")
                if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                    raise ValueError(f"{name}: invalid confidence")
                if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                    raise ValueError(f"{name}: invalid confidence")
                decisions[name] = Decision(choice, float(confidence), normalized)
            if not isinstance(usage, dict):
                raise ValueError("invalid usage")
            for field in ("input_tokens", "output_tokens"):
                if type(usage.get(field)) is not int or usage[field] < 0:
                    raise ValueError(f"invalid usage.{field}")
        except (KeyError, TypeError, ValueError) as error:
            raise BackendError(f"Invalid TypeSafe API response: {error}") from error
        return decisions, {"model": resolved_model, "usage": usage}
