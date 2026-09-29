from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

from . import __version__
from .backend import BackendError, JevBackend
from .config import ConfigError, load_config
from .engine import review, serialize_diagnostics
from .report import render
from .source import discover

DEFAULT_CONFIG = Path(__file__).with_name("default_rules.yaml")


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Advisory semantic review of TypeScript tests using Jev/TypeSafe."
    )
    parser.add_argument("paths", nargs="+", help="TypeScript files or directories")
    parser.add_argument("--config", action="append", default=[], help="YAML overlay")
    parser.add_argument("--rule", action="append", default=[], help="run only this rule")
    parser.add_argument("--exclude", action="append", default=[], help="glob relative to scan root")
    parser.add_argument("--model", help="override the configured Jev model")
    parser.add_argument("--format", choices=("text", "json", "github"), default="text")
    parser.add_argument(
        "--dry-run", action="store_true", help="parse and validate without API calls"
    )
    parser.add_argument("--show-abstentions", action="store_true")
    parser.add_argument("--fail-on-findings", action="store_true")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def scan(args: argparse.Namespace, backend_factory: Any = JevBackend) -> tuple[dict[str, Any], int]:
    started = time.perf_counter()
    config, config_hash = load_config(DEFAULT_CONFIG, args.config, args.rule)
    if args.model:
        config["provider"]["model"] = args.model
        config_hash = hashlib.sha256(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    root, discovery = discover(args.paths, args.exclude)
    diagnostics = list(discovery.diagnostics)
    base_summary: dict[str, Any] = {
        **discovery.counts,
        "tests_extracted": len(discovery.units),
        "planned_questions": len(discovery.units) * len(config["rules"]),
    }
    findings: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    resolved_model: str | None = None
    if args.dry_run:
        summary = {
            **base_summary,
            "requests": 0,
            "questions_scored": 0,
            "findings": 0,
            "flags": 0,
            "warnings": 0,
            "abstentions": 0,
            "errored_tests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "inference_ms": 0.0,
        }
    elif discovery.units:
        provider = config["provider"]
        backend = backend_factory(
            endpoint=provider["endpoint"],
            model=provider["model"],
            timeout_seconds=provider["timeout_seconds"],
            max_retries=provider["max_retries"],
        )
        findings, model_diagnostics, run_summary, decisions = review(
            discovery.units, config, backend
        )
        diagnostics.extend(model_diagnostics)
        summary = {**base_summary, **run_summary}
        if decisions:
            resolved_model = decisions[0]["model"]
    else:
        summary = {
            **base_summary,
            "requests": 0,
            "questions_scored": 0,
            "findings": 0,
            "flags": 0,
            "warnings": 0,
            "abstentions": 0,
            "errored_tests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "inference_ms": 0.0,
        }
    if not discovery.counts["files_supported"]:
        from .types import Diagnostic

        diagnostics.append(Diagnostic("error", "no_supported_files", message="no .ts/.tsx files"))
    report = {
        "schema_version": 1,
        "mode": "dry_run" if args.dry_run else "review",
        "metadata": {
            "tool_version": __version__,
            "provider": "TypeSafe Jev",
            "requested_model": config["provider"]["model"],
            "resolved_model": resolved_model,
            "ruleset_hash": config_hash,
            "display_root": str(root),
            "experimental": True,
            "scores_calibrated": False,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
        },
        "findings": findings,
        "summary": summary,
        "diagnostics": serialize_diagnostics(diagnostics),
    }
    has_error = any(item["kind"] == "error" for item in report["diagnostics"])
    if has_error:
        return report, 2
    if args.fail_on_findings and findings:
        return report, 1
    return report, 0


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    try:
        report, status = scan(args)
    except KeyboardInterrupt:
        return 130
    except (
        BackendError,
        ConfigError,
        ValueError,
        OSError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        if args.format == "json":
            print(json.dumps({"schema_version": 1, "findings": [], "error": str(error)}))
        else:
            print(f"error: {error}", file=sys.stderr)
        return 2
    render(report, args.format, args.show_abstentions)
    return status
