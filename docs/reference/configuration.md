# Configuration reference

Configuration is read from environment variables. The project uses `python-dotenv`, so local development can put non-secret defaults in `.env`. Never commit `.env` or credential files.

Use `uv run anki-chinese doctor` to check whether the local files and optional
credentials needed by the main workflows are present. Add `--check-anki` when
Anki is open to include a read-only AnkiConnect reachability probe.

## Environment variables

| Variable | Required for | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | `sentences`, `keywords`, `sentences repair-confusers --apply` | Gemini API key for sentence generation and meaning repair. |
| `MINIMAX_API_KEY` | MiniMax audio | MiniMax TTS API key. |
| `MINIMAX_API_HOST` | Optional MiniMax override | Use `https://api.minimaxi.com` for mainland-region keys; default is `https://api.minimax.io`. |
| `MINIMAX_TTS_MODEL` | Optional MiniMax override | Override the MiniMax speech model. |
| `MINIMAX_MANDARIN_VOICE_ID` | Optional MiniMax override | Override Mandarin voice. |
| `MINIMAX_CANTONESE_VOICE_ID` | Optional MiniMax override | Override Cantonese voice. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google audio when using service-account auth | Path to a Google Cloud service account JSON file. |
| `GOOGLE_TTS_ENDPOINT` | Optional Google override | Override the Text-to-Speech REST endpoint. |
| `GOOGLE_TTS_MANDARIN_VOICE` | Optional Google override | Override Mandarin voice. |
| `GOOGLE_TTS_CANTONESE_VOICE` | Optional Google override | Override Cantonese voice. |
| `ANKICONNECT_API_KEY` | Optional AnkiConnect auth | API key if your local AnkiConnect add-on requires one. |

## Google Cloud Text-to-Speech auth

The current Google provider uses Application Default Credentials, not an API-key environment variable.

Use one of these:

```bash
gcloud auth application-default login
```

or:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

The service account or ADC user must have access to the Text-to-Speech API in a Google Cloud project where the API is enabled.

## MiniMax auth

```bash
export MINIMAX_API_KEY=your-key
```

Global keys use the default host. Mainland-region keys usually need:

```bash
export MINIMAX_API_HOST=https://api.minimaxi.com
```

## Gemini auth

```bash
export GEMINI_API_KEY=your-key
```

Gemini is only needed for commands that generate or repair sentence/meaning content.

## AnkiConnect auth

No API key is needed with the default AnkiConnect configuration. If you enable an AnkiConnect API key, expose it to the CLI:

```bash
export ANKICONNECT_API_KEY=your-key
```

Keep AnkiConnect bound to localhost unless you intentionally expose it and have configured firewall/API-key protections.
