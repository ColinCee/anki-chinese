# Security

## Secrets

Do not commit:

- `.env`
- API keys
- Google service-account JSON files
- Anki backups or exports that contain private study data unless you intentionally want them public
- generated audio/deck artifacts from `data/build/`

Use environment variables documented in [Reference](docs/reference.md).

## AnkiConnect

AnkiConnect is a local HTTP API for the open Anki collection. Keep it bound to `127.0.0.1` unless you intentionally expose it beyond localhost and have configured firewall/API-key protections.

If you enable an AnkiConnect API key, configure it as described in
[Reference](docs/reference.md#environment-variables).
For live mutations, follow the preview, backup, and undo procedure in
[Workflows](docs/workflows.md#learn-characters-from-songs).

## Reporting issues

For vulnerabilities or accidental secret exposure, open a private security advisory if available for the GitHub repository. If that is not available, contact the maintainer directly rather than posting sensitive details in a public issue.
