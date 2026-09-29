from pathlib import Path

from scripts.run_review_risks import LABELS, build_request, load_cases

ROOT = Path(__file__).resolve().parents[1]


def test_risk_suite_has_29_distinct_checks() -> None:
    document = load_cases(ROOT / "benchmarks" / "review_risks" / "cases.yaml")
    checks = document["checks"]
    assert len(checks) == 29
    assert len({check["title"] for check in checks}) == 29
    assert len({check["rule"] for check in checks}) == 29


def test_request_keeps_cases_isolated_and_exposes_four_outcomes() -> None:
    document = load_cases(ROOT / "benchmarks" / "review_risks" / "cases.yaml")
    state, questions = build_request(document)
    assert "expected:" not in state.lower()
    assert len(questions) == 29
    assert all(set(question["criteria"]) == set(LABELS) for question in questions.values())
