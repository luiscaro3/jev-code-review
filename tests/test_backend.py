from __future__ import annotations

import io
import json

import pytest

from jev_review.backend import BackendError, JevBackend

QUESTION = {
    "relationship": {
        "type": "choice",
        "instructions": "Choose.",
        "criteria": {"yes": "Yes.", "no": "No.", "unknown": "Unknown."},
    }
}


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_validates_a_well_formed_response():
    payload = {
        "model": "jev-1.13.0",
        "answers": {
            "relationship": {
                "type": "choice",
                "choice": "yes",
                "confidence": 0.9,
                "probabilities": {"yes": 0.95, "no": 0.03, "unknown": 0.02},
            }
        },
        "usage": {"input_tokens": 12, "output_tokens": 1},
    }
    backend = JevBackend(
        endpoint="https://example.invalid",
        model="jev-latest",
        timeout_seconds=1,
        max_retries=0,
        api_key="test-only",
        opener=lambda *_args, **_kwargs: Response(json.dumps(payload).encode()),
    )
    decisions, metadata = backend.decide("source", QUESTION)
    assert decisions["relationship"].choice == "yes"
    assert metadata["model"] == "jev-1.13.0"


def test_rejects_unknown_response_labels():
    payload = {
        "model": "jev-1.13.0",
        "answers": {
            "relationship": {
                "type": "choice",
                "choice": "maybe",
                "confidence": 0.9,
                "probabilities": {"yes": 0.5, "no": 0.3, "maybe": 0.2},
            }
        },
        "usage": {"input_tokens": 12, "output_tokens": 1},
    }
    backend = JevBackend(
        endpoint="https://example.invalid",
        model="jev-latest",
        timeout_seconds=1,
        max_retries=0,
        api_key="test-only",
        opener=lambda *_args, **_kwargs: Response(json.dumps(payload).encode()),
    )
    with pytest.raises(BackendError):
        backend.decide("source", QUESTION)


def test_requires_api_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    with pytest.raises(BackendError):
        JevBackend(
            endpoint="https://example.invalid",
            model="jev-latest",
            timeout_seconds=1,
            max_retries=0,
        )
