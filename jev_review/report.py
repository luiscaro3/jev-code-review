from __future__ import annotations

import json
import sys
from typing import Any


def render(report: dict[str, Any], output_format: str, show_abstentions: bool = False) -> None:
    if output_format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if output_format == "github":
        for finding in report["findings"]:
            print(
                f"::warning file={finding['path']},line={finding['start_line']},"
                f"endLine={finding['end_line']},title={finding['rule_name']}::"
                f"{finding['message']} (p={finding['finding_probability']:.3f})"
            )
        return
    for finding in report["findings"]:
        print(
            f"{finding['path']}:{finding['start_line']}-{finding['end_line']}  "
            f"{finding['band']}  p={finding['finding_probability']:.3f}  "
            f"{finding['rule_name']}"
        )
        print(f"  {finding['message']}")
    summary = report["summary"]
    if report["mode"] == "dry_run":
        print(
            f"Dry run: {summary['files_supported']} files, {summary['tests_extracted']} tests, "
            f"{summary['planned_questions']} planned questions; no API call.",
            file=sys.stderr,
        )
    else:
        print(
            f"{summary['files_supported']} files, {summary['tests_extracted']} tests, "
            f"{summary['requests']} API requests, {summary['findings']} findings, "
            f"{summary['abstentions']} abstentions, {summary['errored_tests']} errors.",
            file=sys.stderr,
        )
    for diagnostic in report["diagnostics"]:
        if diagnostic["kind"] == "error" or (
            show_abstentions and diagnostic["kind"] in {"abstain", "skip", "notice"}
        ):
            print(
                f"{diagnostic['kind']}: {diagnostic['path'] or '-'} "
                f"{diagnostic['rule_name'] or '-'} {diagnostic['reason']}: "
                f"{diagnostic['message']}",
                file=sys.stderr,
            )
