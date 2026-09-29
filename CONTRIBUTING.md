# Contributing

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
python -m pytest
```

Keep source extraction deterministic and semantic judgment inside Jev. Do not
infer helper behavior from names or add repository-wide dependency resolution
to make a benchmark pass.

## Rule changes

A new or changed rule requires:

1. A written evidence boundary and explicit `undetermined` definition.
2. Frozen cases with matched semantic changes.
3. Human-reviewed labels.
4. Calibration/test separation.
5. Saved raw predictions and a validation report.

Do not tune thresholds on the same examples used to report final results.
