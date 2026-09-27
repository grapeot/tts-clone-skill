# TTS Clone Skill

Clone an adult voice and synthesize new audio using two engines:

- Gemini 3.8 Flash TTS voice replication, through the Gemini API.
- Qwen3-TTS 12 Hz 1.7B Base, running locally from the open-source weights.

This package provides a CLI and an agent skill. It ships without voice samples, voice keys, or API credentials.

## Install

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
```

Local Qwen cloning is optional and heavy:

```bash
uv pip install -e '.[qwen]'
```

To install via a coding agent, pass the repository URL. The agent should inspect the workspace `AGENTS.md` or `CLAUDE.md`, follow any skills index, and expose only `skills/tts_clone.md` as the root skill.

## Configure Gemini

Generate an API key in Google AI Studio and export it before running live commands:

```bash
export GEMINI_API_KEY=replace-with-your-gemini-api-key
```

If both `GEMINI_API_KEY` and `GOOGLE_API_KEY` are present, this CLI uses `GEMINI_API_KEY` and reports that both are set. The official Python SDK prefers `GOOGLE_API_KEY` under the same conditions. Do not assume both variables hold the same key.

Voice replication is available on both free and paid Gemini API tiers and requires consent verification. Verify current pricing before estimating costs. On 2026-09-26, the pricing page listed `gemini-3.8-flash-tts` Standard audio output at $9.00 per 1M tokens through 2026-12-31, equivalent to $0.00225 per 10 seconds. That same page marked the free tier as used to improve products.

## Record

Record two separate clips from the same adult using the same microphone during the same sitting. Do not move the recording device between takes.

The reference clip must be 10 to 30 seconds of clean, single-speaker speech. The consent clip must contain only the official sentence for a supported locale. Verified sentences:

- `zh-CN`: 我是此声音的拥有者并授权谷歌使用此声音创建语音合成模型
- `en-US`: I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model.

The remaining 28 locales are listed in the [voice replication docs](https://ai.google.dev/gemini-api/docs/voice-replication). Do not paraphrase.

```bash
python -m tts_clone prepare reference.m4a -o reference.wav --role reference
python -m tts_clone prepare consent.m4a -o consent.wav --role consent
python -m tts_clone inspect reference.wav --role reference
```

`prepare` generates 24 kHz mono 16-bit WAV files, matching the format recommended in the Gemini documentation.

## Gemini

```bash
python -m tts_clone gemini-replicate \
  --source reference.wav \
  --consent consent.wav \
  --out-key private/voicekey.txt

python -m tts_clone gemini-speak \
  --voice-key-file private/voicekey.txt \
  --text "A short line the listener has not heard in the reference." \
  --language zh-CN \
  -o sample.wav
```

Adding `--store` asks Google to retain a `voice_` id for one year. The project cap is 200 stored voices, shared with prompted voices. Without `--store`, the API returns a client-held `voicekey_` documented as valid for 7 days. The CLI writes the secret to `--out-key` and never prints it to stdout.

## Private assets and the 7-day key

The client-held key expires after about 7 days. Keep per-speaker assets in a `private/` directory that git never sees:

```text
private/
├── reference.wav   # or reference.m4a
├── consent.wav     # or consent.m4a
├── reference.txt   # verbatim transcript, for Qwen
└── voicekey.txt    # + voicekey.txt.created (ISO-8601 UTC)
```

`gemini-speak` can resolve that directory by itself when `--voice-key-file` is omitted:

```bash
cd <repo checkout>
python -m tts_clone gemini-speak \
  --private-dir private \
  --text-file line.txt \
  --language zh-CN \
  -o out.wav
```

It uses the key when the stamp is at most 7 days old. When the key is missing or stale, it converts the m4a reference and consent into `private/prepared/*.wav` and re-runs replication, so a stale key does not require re-recording; the original audio is the fallback. Voice replication in AI Studio is unavailable in Illinois, Texas, the EEA, the UK, Switzerland, and India. The voice-replication API documentation does not repeat that list.

## Qwen3-TTS

```bash
python -m tts_clone qwen-clone \
  --ref-audio reference.wav \
  --ref-text-file reference.txt \
  --text-file line.txt \
  -o qwen.wav
```

`reference.txt` must contain a verbatim transcript of the reference clip. The default model is `Qwen/Qwen3-TTS-12Hz-1.7B-Base`. On machines without CUDA, the CLI uses MPS if available, otherwise CPU. Both paths use `sdpa` attention. Do not require `flash-attn` on macOS.

## Output

Every command outputs a single JSON object with `command`, `input`, `data`, and `error`. Exit codes indicate status: 0 for success, 2 for usage or local tool failures, 10 for a missing or rejected key, 12 for Gemini HTTP 400 or 500, and 13 for other HTTP failures. A consent or speaker rejection arrives as 12, sometimes wrapped in a 500.

Never commit reference audio, consent audio, voice keys, or generated speech that identifies a private speaker.
