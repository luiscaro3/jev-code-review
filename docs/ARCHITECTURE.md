# Architecture

## Invariants

- Source files are read but never executed.
- Tree-sitter extracts exact complete test calls; semantic decisions stay in Jev.
- Both configured rules are asked in one request per test.
- A finding is emitted only when Jev selects that rule's configured
  `finding_choice` and its score meets `warning_probability`.
- `insufficient_evidence` is preserved as an abstention, not converted into a pass.
- API responses are rejected if answer names, choices, probabilities, or
  confidence values do not match the request contract.
- HTTP retries apply only to transport failures, rate limits, and 5xx responses.

## Components

| Module | Responsibility |
|---|---|
| `source.py` | Safe file discovery and TypeScript/TSX test extraction |
| `config.py` | Strict YAML, overlays, rule selection, ruleset hash |
| `backend.py` | Authenticated Jev request, retry policy, response validation |
| `engine.py` | Per-test batching, findings, abstentions, metrics |
| `report.py` | Text, JSON, and GitHub annotation output |
| `cli.py` | User interface, exit codes, operational report |

## Trust boundary

The local parser and configuration loader are trusted. Source comments remain
untrusted model input; delimiters are not a security boundary. The TypeSafe API
is an external processor and receives each extracted test verbatim.

API keys are read only from `TYPESAFE_API_KEY` or `JEV_API_KEY`. They are never
written to reports, benchmark files, or configuration.
