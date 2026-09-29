"""Batch all enabled semantic questions into one Jev request per test."""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from .config import question
from .types import CodeUnit, Diagnostic


def review(
    units: list[CodeUnit], config: dict[str, Any], backend: Any
) -> tuple[list[dict[str, Any]], list[Diagnostic], dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    diagnostics: list[Diagnostic] = []
    decisions_log: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "tests_reviewed": 0,
        "requests": 0,
        "questions_scored": 0,
        "abstentions": 0,
        "findings": 0,
        "flags": 0,
        "warnings": 0,
        "errored_tests": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "inference_ms": 0.0,
    }
    rules = config["rules"]
    questions = {name: question(rule) for name, rule in rules.items()}
    for unit in units:
        started = time.perf_counter()
        try:
            decisions, metadata = backend.decide(unit.source_text, questions)
        except Exception as error:
            summary["errored_tests"] += 1
            diagnostics.append(
                Diagnostic(
                    "error",
                    "inference_error",
                    unit.source.display_path,
                    message=f"{type(error).__name__}: {error}",
                )
            )
            continue
        elapsed_ms = (time.perf_counter() - started) * 1000
        summary["tests_reviewed"] += 1
        summary["requests"] += 1
        summary["questions_scored"] += len(decisions)
        summary["inference_ms"] += elapsed_ms
        usage = metadata.get("usage", {})
        summary["input_tokens"] += int(usage.get("input_tokens", 0) or 0)
        summary["output_tokens"] += int(usage.get("output_tokens", 0) or 0)
        for name, decision in decisions.items():
            rule = rules[name]
            finding_probability = decision.probabilities[rule["finding_choice"]]
            decisions_log.append(
                {
                    "path": unit.source.display_path,
                    "start_line": unit.start_line,
                    "end_line": unit.end_line,
                    "rule_name": name,
                    "choice": decision.choice,
                    "confidence": decision.confidence,
                    "probabilities": decision.probabilities,
                    "model": metadata["model"],
                    "elapsed_ms": elapsed_ms,
                }
            )
            if decision.choice == rule["unknown_choice"]:
                summary["abstentions"] += 1
                diagnostics.append(
                    Diagnostic(
                        "abstain",
                        "insufficient_visible_evidence",
                        unit.source.display_path,
                        name,
                        "Jev selected the rule's undetermined outcome.",
                    )
                )
                continue
            if decision.choice != rule["finding_choice"]:
                continue
            if finding_probability < rule["warning_probability"]:
                diagnostics.append(
                    Diagnostic(
                        "notice",
                        "below_warning_probability",
                        unit.source.display_path,
                        name,
                        f"Selected finding choice at {finding_probability:.3f}.",
                    )
                )
                continue
            band = "FLAG" if finding_probability >= rule["flag_probability"] else "WARN"
            summary["findings"] += 1
            summary["flags" if band == "FLAG" else "warnings"] += 1
            findings.append(
                {
                    "path": unit.source.display_path,
                    "symbol": unit.symbol,
                    "unit_kind": unit.kind,
                    "start_line": unit.start_line,
                    "end_line": unit.end_line,
                    "rule_name": name,
                    "choice": decision.choice,
                    "band": band,
                    "finding_probability": finding_probability,
                    "confidence": decision.confidence,
                    "message": rule["message"],
                }
            )
    findings.sort(key=lambda item: (item["path"], item["start_line"], item["rule_name"]))
    return findings, diagnostics, summary, decisions_log


def serialize_diagnostics(diagnostics: list[Diagnostic]) -> list[dict[str, Any]]:
    return [asdict(diagnostic) for diagnostic in diagnostics]
