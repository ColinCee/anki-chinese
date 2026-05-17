# Security

## Secrets

Do not commit:

- `.env`
- API keys
- Google service-account JSON files
- Anki backups or exports that contain private study data unless you intentionally want them public
- generated audio/deck artifacts from `data/build/`

Use environment variables documented in [Configuration reference](docs/reference/configuration.md).

## AnkiConnect

AnkiConnect is a local HTTP API for the open Anki collection. Keep it bound to `127.0.0.1` unless you intentionally expose it beyond localhost and have configured firewall/API-key protections.

If you enable an AnkiConnect API key, set:

```bash
export ANKICONNECT_API_KEY=your-key
```

Live activation commands mutate the open Anki collection. Always dry-run first and keep an Anki backup or undo path.

## Reporting issues

For vulnerabilities or accidental secret exposure, open a private security advisory if available for the GitHub repository. If that is not available, contact the maintainer directly rather than posting sensitive details in a public issue.
