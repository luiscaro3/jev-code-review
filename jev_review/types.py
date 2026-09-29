from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceFile:
    path: Path
    display_path: str
    raw: bytes
    text: str
    sha256: str
    tree: Any


@dataclass(frozen=True)
class CodeUnit:
    source: SourceFile
    symbol: str
    kind: str
    start_byte: int
    end_byte: int
    start_line: int
    end_line: int
    source_text: str


@dataclass(frozen=True)
class Decision:
    choice: str
    confidence: float
    probabilities: dict[str, float]


@dataclass
class Diagnostic:
    kind: str
    reason: str
    path: str | None = None
    rule_name: str | None = None
    message: str = ""


@dataclass
class Discovery:
    files: list[SourceFile] = field(default_factory=list)
    units: list[CodeUnit] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    counts: dict[str, int] = field(
        default_factory=lambda: {
            "files_discovered": 0,
            "files_supported": 0,
            "files_excluded": 0,
            "files_unsupported": 0,
            "files_errored": 0,
        }
    )
