from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def benchmark_rows():
    def load(module: str) -> list[dict]:
        path = ROOT / "benchmarks" / module / "predictions.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    return load
