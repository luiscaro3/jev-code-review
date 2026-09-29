#!/usr/bin/env python3
"""Run the 29-case synthetic review-risk demonstration through Jev."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from jev_review.backend import JevBackend

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "benchmarks" / "review_risks" / "cases.yaml"
EXPECTED_IDS = tuple(f"R{index:02d}" for index in range(1, 30))
LABELS = ("risk_present", "no_risk", "not_applicable", "insufficient_evidence")


def load_cases(path: Path) -> dict:
    document = yaml.safe_load(path.read_text())
    checks = document.get("checks", [])
    if tuple(check.get("id") for check in checks) != EXPECTED_IDS:
        raise ValueError("risk suite must contain R01-R29 exactly once in order")
    for check in checks:
        for field in ("domain", "title", "rule", "evidence", "code"):
            if not isinstance(check.get(field), str) or not check[field].strip():
                raise ValueError(f"{check['id']}: nonempty {field} required")
    return document


def build_request(document: dict) -> tuple[str, dict]:
    checks = document["checks"]
    state = "\n\n".join(
        (
            f"[{check['id']}] {check['title']}\n"
            f"Context:\n{check['evidence']}\n\nPR excerpt:\n{check['code']}"
        )
        for check in checks
    )
    questions = {
        f"risk_{check['id'].lower()}": {
            "type": "choice",
            "instructions": (
                f"Evaluate only [{check['id']}] against this review rule: {check['rule']} "
                "Use only the supplied context and PR excerpt."
            ),
            "criteria": {
                "risk_present": "The supplied evidence establishes the prohibited condition.",
                "no_risk": (
                    "The rule applies and the supplied evidence establishes that it is satisfied."
                ),
                "not_applicable": "The rule does not apply to the supplied change.",
                "insufficient_evidence": (
                    "The rule applies, but the supplied evidence is not enough to decide."
                ),
            },
        }
        for check in checks
    }
    return state, questions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    document = load_cases(args.cases)
    state, questions = build_request(document)
    if args.dry_run:
        print(json.dumps({"checks": 29, "calls": 1, "model": args.model}, indent=2))
        return

    backend = JevBackend(
        endpoint="https://api.typesafe.ai/v1/systemone",
        model=args.model,
        timeout_seconds=90,
        max_retries=4,
    )
    decisions, metadata = backend.decide(state, questions)
    rows = []
    for check in document["checks"]:
        decision = decisions[f"risk_{check['id'].lower()}"]
        rows.append(
            {
                "id": check["id"],
                "domain": check["domain"],
                "title": check["title"],
                "choice": decision.choice,
                "confidence": decision.confidence,
                "probabilities": decision.probabilities,
            }
        )
    result = {"model": metadata["model"], "usage": metadata["usage"], "results": rows}
    output = args.output or ROOT / "runs" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
