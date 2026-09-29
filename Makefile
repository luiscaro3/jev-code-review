.PHONY: check test lint demo-dry suite-dry

check: lint test suite-dry demo-dry

lint:
	.venv/bin/ruff check .

test:
	.venv/bin/python -m pytest

suite-dry:
	.venv/bin/python scripts/run_review_risks.py --dry-run

demo-dry:
	.venv/bin/jev-review examples/demo --dry-run
