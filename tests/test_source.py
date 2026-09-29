from pathlib import Path

from jev_review.source import discover


def test_extracts_active_tests_and_omits_groups_and_inactive_tests(tmp_path: Path):
    source = tmp_path / "example.test.ts"
    source.write_text(
        """describe("group", () => {
  test("active", () => { expect(1).toBe(1); });
  it.skip("skipped", () => { expect(1).toBe(2); });
  test.concurrent("concurrent", async () => { expect(await work()).toBe(1); });
});
"""
    )
    _, discovery = discover([str(source)])
    assert len(discovery.units) == 2
    assert all(unit.kind == "test" for unit in discovery.units)
    assert any(item.reason == "inactive_test" for item in discovery.diagnostics)


def test_supports_tsx_and_rejects_parse_errors(tmp_path: Path):
    (tmp_path / "component.test.tsx").write_text(
        'test("renders", () => { expect(<Button />).toBeTruthy(); });\n'
    )
    (tmp_path / "broken.test.ts").write_text('test("broken", () => {\n')
    _, discovery = discover([str(tmp_path)])
    assert len(discovery.units) == 1
    assert discovery.counts["files_errored"] == 1
