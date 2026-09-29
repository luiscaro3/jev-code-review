# Validation

## Automated contracts

The test suite verifies:

- strict YAML parsing and overlay validation;
- TypeScript and TSX test extraction;
- inactive and parameterized-test handling;
- one Jev request for both production questions per test;
- response schema and probability validation;
- missing-key behavior;
- JSON reporting and operational exit contracts; and
- the shape, uniqueness, labels, and request construction of the 29-risk suite.

Run all offline checks:

```bash
python -m pytest
ruff check .
python scripts/run_review_risks.py --dry-run
```

## What the current evidence establishes

The checks establish deterministic extraction, request construction, response
validation, reporting, and end-to-end behavior with a controlled backend. The
live playground demonstrates that Jev can evaluate the synthetic suite.

They do not establish real-repository precision, recall, calibration, or
fitness as a blocking quality gate. The revised rules and examples invalidate
scores produced for any earlier prompts.

## Promotion gate

Before blocking merges:

1. Freeze a diverse corpus before inspecting model output.
2. Have engineers label it without seeing Jev's decisions.
3. Separate calibration and untouched test partitions.
4. Report precision, recall, abstention rate, and confidence intervals.
5. Re-run the evaluation after any prompt, model, or evidence-format change.
