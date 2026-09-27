# Working

## Changelog

### 2026-09-26

- Initial release of the public CLI and skill supporting Gemini 3.8 Flash TTS voice replication and local Qwen3-TTS 1.7B Base cloning.
- Ships without bundled voice samples.
- Raised `requires-python` to `>=3.10` after CI failed resolving the optional Qwen extra on the 3.9 marker.
- Added the `private/` convention: `gemini-speak` resolves a fresh `voicekey.txt` first, then falls back to `reference` and `consent` clips (WAV preferred, m4a converted into `private/prepared/`), re-replicating when the 7-day key has expired.

## Lessons Learned

- Gemini voice creation failures can manifest as HTTP 500 with `Error translating server response to JSON`. The actionable error text is located in the nested `Original error`.
- Phrase matching and speaker matching are independent checks. A consent clip may fail phrase verification even if an independent transcription engine recognizes the official sentence. Speaker matching can fail when the two recordings are taken in separate sittings, even with the same hardware.
- The API rejects `response_modalities: ["AUDIO"]`. Calls must use `response_format: {"type": "audio"}`.
- Versions of `google-genai` older than 2.25.0 do not include a voices client. This CLI avoids a dependency on that package.
- When both `GEMINI_API_KEY` and `GOOGLE_API_KEY` are configured, the official SDK defaults to `GOOGLE_API_KEY`. This CLI prioritizes `GEMINI_API_KEY`.
- Qwen cloning fidelity depends on an accurate, verbatim `ref_text`. Do not declare `flash-attn` as a required dependency on macOS; use `sdpa`.
- Pricing terms and regional availability remain subject to change. On 2026-09-26, the pricing documentation listed Flash TTS paid audio output at $9.00 per 1M tokens through 2026-12-31. Always consult the official pricing page directly before quoting rates.
- An optional extra that needs a newer Python than `requires-python` still breaks `uv pip install -e '.[dev]'`. uv resolves every extra against the project's Python range. The Qwen extra needs Python 3.10, so the floor is `>=3.10`.
