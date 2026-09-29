# Demo guide

## Live playground

Open <https://jev-review-lab.luis-marchesi.chatgpt.site/>. Choose a synthetic
PR excerpt, inspect its editable review rule, and run one check. Then run the
full 29-risk suite to see one batched Jev evaluation across distinct review
concerns.

The live result must be described as model output on synthetic inputs, not as
measured production accuracy.

## Local CLI

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
export TYPESAFE_API_KEY="your-test-key"
jev-review examples/demo --show-abstentions
```

The demo includes a test that calls its own programmed stub, a test that checks
an adjacent error property, one test that reaches product logic, and one whose
helper hides the decisive evidence.

Machine-readable and CI-oriented output:

```bash
jev-review examples/demo --format json > review.json
jev-review examples/demo --format github --fail-on-findings
```

## Credential-free verification

```bash
jev-review examples/demo --dry-run
python scripts/run_review_risks.py --dry-run
python -m pytest
ruff check .
```

Presenter constraints:

- Say “potential semantic review risk,” not “confirmed bug.”
- State that submitted source is sent to TypeSafe.
- Do not describe a quiet result as proof of correctness.
- Keep abstention visible when the supplied evidence is incomplete.
- Call this a working demonstration pending blind external validation.
