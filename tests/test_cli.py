from pathlib import Path

from jev_review.cli import arguments, scan
from jev_review.types import Decision


class FindingBackend:
    def __init__(self, **_kwargs):
        pass

    def decide(self, _state, questions):
        decisions = {}
        for name, specification in questions.items():
            selected = "test_double_only" if name == "Product logic exercised" else "adjacent_only"
            decisions[name] = Decision(
                selected,
                0.99,
                {
                    choice: 0.98 if choice == selected else 0.01
                    for choice in specification["criteria"]
                },
            )
        return decisions, {
            "model": "jev-test",
            "usage": {"input_tokens": 12, "output_tokens": 2},
        }


def test_dry_run_needs_no_credentials(tmp_path: Path):
    source = tmp_path / "sample.test.ts"
    source.write_text('test("works", () => { expect(run()).toBe(true); });\n')
    report, status = scan(arguments([str(source), "--dry-run", "--format", "json"]))
    assert status == 0
    assert report["summary"]["tests_extracted"] == 1
    assert report["summary"]["planned_questions"] == 2
    assert report["summary"]["requests"] == 0


def test_no_supported_files_is_operational_error(tmp_path: Path):
    (tmp_path / "readme.md").write_text("nothing")
    report, status = scan(arguments([str(tmp_path), "--dry-run"]))
    assert status == 2
    assert any(item["reason"] == "no_supported_files" for item in report["diagnostics"])


def test_end_to_end_findings_and_ci_exit(tmp_path: Path):
    source = tmp_path / "sample.test.ts"
    source.write_text(
        'test("returns code LOCKED", () => { expect(error).toBeInstanceOf(Error); });\n'
    )
    args = arguments([str(source), "--fail-on-findings"])
    report, status = scan(args, backend_factory=FindingBackend)
    assert status == 1
    assert len(report["findings"]) == 2
    assert report["summary"]["requests"] == 1
    assert report["metadata"]["resolved_model"] == "jev-test"
