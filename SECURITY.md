# Security policy

## Data handling

This tool sends each extracted TypeScript test to the configured TypeSafe API
endpoint. It does not redact source. Do not review secrets, credentials, or
code your organization has not approved for external processing.

API credentials must be supplied through `TYPESAFE_API_KEY` or `JEV_API_KEY`.
Never put a key in YAML, source files, command history, screenshots, issues, or
benchmark artifacts. Rotate any key exposed in chat or a repository.

JSON output includes the absolute local scan root in metadata. Remove that
field before publishing reports if local paths are sensitive.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or exposed key. Use a
private security advisory after the repository is created on GitHub.
