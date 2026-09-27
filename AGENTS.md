# AGENTS.md

This repository contains a public skill. English is the working language, and the default branch is `master`.

## Commands

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
python -m tts_clone --help
python -m pytest tests/ -v
```

Qwen model weights are excluded from default test runs. Install `.[qwen]` only when performing local voice clones.

## Invariants

- Every command emits exactly one JSON object on stdout.
- Never print `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or a `voicekey_` / `voice_` secret. Save the voice secret strictly to the file specified by the caller.
- Exit codes: 0 for success, 2 for usage or local failure, 10 for a missing or rejected key, 12 for Gemini HTTP 400 or 500, and 13 for other HTTP failures.
- Never commit voice samples, generated private speech clips, or real credentials to git.
- Public examples must use `example.com` placeholders and `replace-with-your-gemini-api-key`.
- After any meaningful change, record a dated entry in `docs/working.md`.

## Layout

- `skills/tts_clone.md` is the only skill file to register in a workspace index.
- `src/tts_clone/` contains the CLI implementation.
- `docs/` stores product requirements, architecture notes, and test plans.
- Per-speaker assets (reference, consent, voice key, transcripts) belong in `private/`, which is gitignored. Never stage it.
