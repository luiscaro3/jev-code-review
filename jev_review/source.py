"""Read-only TypeScript discovery and Tree-sitter test extraction."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from pathlib import Path
from typing import Any

import tree_sitter_typescript
from tree_sitter import Language, Parser

from .types import CodeUnit, Diagnostic, Discovery, SourceFile

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    ".next",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "venv",
}
MAX_SOURCE_BYTES = 1024 * 1024
_TS = Language(tree_sitter_typescript.language_typescript())
_TSX = Language(tree_sitter_typescript.language_tsx())


def _parser(path: Path) -> Parser:
    return Parser(_TSX if path.suffix == ".tsx" else _TS)


def _slice(raw: bytes, node: Any) -> str:
    return raw[node.start_byte : node.end_byte].decode("utf-8")


def _test_kind(raw: bytes, node: Any) -> tuple[str, str] | None:
    if node.type != "call_expression":
        return None
    function = node.child_by_field_name("function")
    if function is None:
        return None
    value = _slice(raw, function)
    base = value.split(".", 1)[0]
    if base not in {"test", "it", "describe"}:
        return None
    suffix = value[len(base) :]
    if ".each" in suffix:
        return "deferred", "parameterized_test"
    segments = {segment for segment in suffix.split(".") if segment}
    if not segments.issubset({"only", "skip", "todo", "concurrent", "failing"}):
        return None
    if "skip" in segments or "todo" in segments:
        return base, "inactive"
    return base, "active"


def _span(source: SourceFile, node: Any) -> tuple[int, int]:
    start = node.start_byte
    line_start = source.raw.rfind(b"\n", 0, start) + 1
    cursor = line_start
    while cursor:
        previous_end = cursor - 1
        previous_start = source.raw.rfind(b"\n", 0, previous_end) + 1
        line = source.raw[previous_start:previous_end].strip()
        if not line or not line.startswith((b"//", b"/*", b"*", b"*/")):
            break
        cursor = previous_start
    return cursor, node.end_byte


def extract_tests(source: SourceFile) -> tuple[list[CodeUnit], list[Diagnostic]]:
    units: list[CodeUnit] = []
    diagnostics: list[Diagnostic] = []

    def visit(node: Any) -> None:
        match = _test_kind(source.raw, node)
        if match:
            base, state = match
            if base == "deferred":
                diagnostics.append(
                    Diagnostic(
                        "skip",
                        state,
                        source.display_path,
                        message="test.each is not supported",
                    )
                )
                return
            if base == "describe":
                for child in node.named_children:
                    if child.type == "arguments":
                        for argument in child.named_children:
                            if argument.type in {"arrow_function", "function_expression"}:
                                for nested in argument.named_children:
                                    visit(nested)
                return
            if state == "inactive":
                diagnostics.append(
                    Diagnostic(
                        "skip",
                        "inactive_test",
                        source.display_path,
                        message="skipped test omitted",
                    )
                )
                return
            start, end = _span(source, node)
            start_line = source.raw.count(b"\n", 0, start) + 1
            end_line = source.raw.count(b"\n", 0, max(start, end - 1)) + 1
            units.append(
                CodeUnit(
                    source=source,
                    symbol=f"{base}@{node.start_point.row + 1}:{node.start_point.column + 1}",
                    kind="test",
                    start_byte=start,
                    end_byte=end,
                    start_line=start_line,
                    end_line=end_line,
                    source_text=source.raw[start:end].decode("utf-8"),
                )
            )
            return
        for child in node.named_children:
            visit(child)

    visit(source.tree.root_node)
    unique = {(unit.start_byte, unit.end_byte): unit for unit in units}
    return sorted(unique.values(), key=lambda unit: unit.start_byte), diagnostics


def read_source(path: Path, display_path: str) -> SourceFile:
    raw = path.read_bytes()
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("source_over_1mib")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("utf8_bom_unsupported")
    if b"\0" in raw:
        raise ValueError("nul_byte")
    text = raw.decode("utf-8")
    tree = _parser(path).parse(raw)
    if tree.root_node.has_error:
        raise ValueError("typescript_parse_error")
    return SourceFile(path, display_path, raw, text, hashlib.sha256(raw).hexdigest(), tree)


def discover(paths: list[str], excludes: list[str] | None = None) -> tuple[Path, Discovery]:
    excludes = excludes or []
    resolved: list[Path] = []
    for item in paths:
        path = Path(item)
        if path.is_symlink():
            raise ValueError(f"explicit symlink unsupported: {item}")
        if not path.exists():
            raise ValueError(f"path not found: {item}")
        if not (path.is_file() or path.is_dir()):
            raise ValueError(f"not a file or directory: {item}")
        resolved.append(path.resolve())

    root = Path(
        os.path.commonpath([str(path if path.is_dir() else path.parent) for path in resolved])
    )
    result = Discovery()
    seen: set[Path] = set()

    def excluded(relative: str) -> bool:
        return any(fnmatch.fnmatchcase(relative, pattern) for pattern in excludes)

    def candidate(path: Path) -> None:
        if path in seen:
            return
        seen.add(path)
        relative = path.relative_to(root).as_posix()
        result.counts["files_discovered"] += 1
        if excluded(relative):
            result.counts["files_excluded"] += 1
            return
        if path.suffix not in {".ts", ".tsx"} or path.name.endswith(".d.ts"):
            result.counts["files_unsupported"] += 1
            return
        result.counts["files_supported"] += 1
        try:
            source = read_source(path, relative)
            result.files.append(source)
            units, diagnostics = extract_tests(source)
            result.units.extend(units)
            result.diagnostics.extend(diagnostics)
        except (OSError, UnicodeError, ValueError) as error:
            result.counts["files_errored"] += 1
            result.diagnostics.append(
                Diagnostic("error", "source_error", relative, message=str(error))
            )

    for path in resolved:
        if path.is_file():
            candidate(path)
            continue
        for base, directories, files in os.walk(path, followlinks=False):
            base_path = Path(base)
            directories[:] = sorted(
                directory
                for directory in directories
                if directory not in IGNORED_DIRECTORIES
                and not (base_path / directory).is_symlink()
                and not excluded((base_path / directory).relative_to(root).as_posix())
            )
            for name in sorted(files):
                file_path = base_path / name
                if not file_path.is_symlink():
                    candidate(file_path)
    result.files.sort(key=lambda file: file.display_path)
    result.units.sort(key=lambda unit: (unit.source.display_path, unit.start_byte))
    return root, result
