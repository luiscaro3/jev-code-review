from pathlib import Path

from jev_review.config import load_config
from jev_review.engine import review
from jev_review.source import discover
from jev_review.types import Decision

ROOT = Path(__file__).resolve().parents[1]


class FakeBackend:
    def decide(self, _state, questions):
        decisions = {}
        for name, specification in questions.items():
            choices = list(specification["criteria"])
            selected = "test_double_only" if name == "Product logic exercised" else "adjacent_only"
            decisions[name] = Decision(
                selected,
                0.95,
                {choice: 0.98 if choice == selected else 0.01 for choice in choices},
            )
        return decisions, {"model": "jev-test", "usage": {"input_tokens": 10, "output_tokens": 2}}


def test_batches_both_rules_in_one_request(tmp_path: Path):
    source = tmp_path / "sample.test.ts"
    source.write_text(
        'test("returns code LOCKED", () => { expect(error).toBeInstanceOf(Error); });\n'
    )
    _, discovery = discover([str(source)])
    config, _ = load_config(ROOT / "jev_review" / "default_rules.yaml")
    findings, diagnostics, summary, decisions = review(discovery.units, config, FakeBackend())
    assert not diagnostics
    assert len(findings) == 2
    assert summary["requests"] == 1
    assert summary["questions_scored"] == 2
    assert len(decisions) == 2
