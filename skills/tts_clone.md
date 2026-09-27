# TTS Clone

## Goal

Synthesize a new spoken line in an authorized adult speaker's voice using either Gemini 3.8 Flash TTS voice replication or a local Qwen3-TTS clone, keeping secrets off stdout and ensuring private audio is never stored in the repository.

## When to use

Use this skill to clone a voice you are authorized to use, compare Gemini replication with open-source Qwen3-TTS, or generate short listening samples from a reference clip.

Do not use this skill without a matching consent recording, with ambient or household background recordings, or to commit audio, voice keys, or private speech transcripts.

## Acceptance

A task is complete only when all of the following conditions are met:

- The reference file features a single adult speaker (10 to 30 seconds), and a separate consent file is provided for Gemini.
- The Gemini consent clip contains the exact official sentence rather than a paraphrase. Verified locales can be checked with `python -m tts_clone phrases`.
- Reference and consent audio were recorded on the same device and in the same room during a single sitting, without shifts in distance or acoustic environment.
- The CLI JSON output contains neither the API key nor the voice key. The secret key is written solely to the file passed to `--out-key`.
- The output WAV exists, has a duration greater than zero, and is not simply a renamed reference file.
- For Qwen, `ref_text` is an accurate transcript of the reference clip, not the line to synthesize.
- For a script of many lines: every line has a non-empty WAV, and each take has been transcribed back and compared with its text, with every difference judged as recogniser noise (same sound) or a misreading (different sound) and misreadings re-voiced.

## Resources

- CLI: `python -m tts_clone`, after installing via `uv pip install -e .` in this repository.
- Verified Gemini model ID (as of 2026-09-26): `gemini-3.8-flash-tts`. Also available: `gemini-3.8-flash-lite-tts`. Re-check documentation if either ID returns a 404.
- Qwen clone model: `Qwen/Qwen3-TTS-12Hz-1.7B-Base`. Upstream package: `qwen-tts`. Optional dependencies: `uv pip install -e '.[qwen]'`.
- Qwen batch mode: `qwen-clone --lines-file lines.json --out-dir takes/ [--suffix _b]` loads the model and encodes the reference once for all lines.
- Gemini API key: `GEMINI_API_KEY` environment variable, generated in Google AI Studio. Never read credentials from chat transcripts or write them into the repository.
- Official documentation: https://ai.google.dev/gemini-api/docs/voice-replication
- Pricing documentation (verify before quoting): https://ai.google.dev/gemini-api/docs/pricing
- Qwen repository: https://github.com/QwenLM/Qwen3-TTS

## Boundaries

- Gemini replication requires two authentic human recordings from the same adult: `source_audio` and `consent_audio`.
- A 10 to 30 second reference clip is not sufficient on its own. The consent recording must recite one of the 30 official sentences verbatim:
- `zh-CN`: 我是此声音的拥有者并授权谷歌使用此声音创建语音合成模型
- `en-US`: I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model.
- Do not invent sentences for the remaining 28 locales. `python -m tts_clone phrases` returns only the two sentences above. The other locales are on the voice-replication page.
- Do not submit ambient noise, overlapping voices, background music, or recordings of minors.
- Unpaid Gemini API and unpaid AI Studio tiers may use submitted data for product improvement. Linking a billed Google Cloud project classifies AI Studio usage as a paid service even when the nominal price is zero. Confirm billing configuration before uploading voice data.
- Specifying `store=false` returns a client-held `voicekey_` with a documented 7-day TTL. Specifying `store=true` returns a `voice_` id stored for 1 year. The cap is 200 voices per project, shared with prompted voices, and a stored voice can be deleted. The CLI defaults to `store=false`.
- AI Studio voice replication is not supported in Illinois, Texas, the EEA, the UK, Switzerland, and India. This regional restriction is an AI Studio footnote; do not assume the raw API enforces the same geographic block unless explicitly noted on the voice-replication page.
- Qwen does not use Google's consent sentence, but still requires an authorized reference voice. Always provide `ref_text`. Running in `x_vector_only_mode` degrades synthesis quality and is not the default.
- On macOS, load Qwen with `attn_implementation="sdpa"` and `device_map="mps"` when MPS is available. Do not require `flash-attn` on macOS.
- Never commit audio files, voice keys, or private transcripts. The repository `.gitignore` blocks common audio extensions and `voice.key` names, but you must still inspect `git status`.

## Method

Prefer the CLI over manual HTTP requests. Follow this execution order: inspect audio duration, prepare a 24 kHz mono WAV file, replicate the voice, and synthesize a line not present in the reference clip. For comparison, run Qwen on the same reference audio and target text.

Keep caller-specific assets in a `private/` directory beside the repo checkout and treat it as untracked. `.gitignore` already blocks `private/` and common audio extensions. The convention inside `private/`:

- `reference.wav` or `reference.m4a`: the 10 to 30 second reference clip.
- `consent.wav` or `consent.m4a`: the exact official consent sentence.
- `reference.txt`: verbatim transcript of the reference clip, for Qwen.
- `voicekey.txt` plus `voicekey.txt.created`: the client-held key and its ISO-8601 UTC creation stamp.

`gemini-speak` resolves assets in this order when `--voice-key-file` is omitted:

1. `private/voicekey.txt` if the `.created` stamp (or file mtime) is at most 7 days old.
2. Otherwise `reference` and `consent` in `private/`, preferring WAV over m4a, converting non-WAV into `private/prepared/`, then running replication and writing a fresh key.
3. If neither the key nor both clips exist, the command fails with usage naming the missing files.

`gemini-replicate` writes `voicekey.txt.created` next to `--out-key`. A key without a stamp is dated by file mtime.

If Gemini returns an HTTP 500 status with `Error translating server response to JSON`, inspect the nested `Original error` field. In a live call on 2026-09-26, this wrapper concealed an underlying 400 consent rejection. Phrase mismatch and speaker mismatch are distinct failures. A Chinese consent recording can fail the phrase check even if another speech-to-text model transcribes the official sentence correctly. An English consent recording may pass phrase verification but fail speaker matching if not recorded in the same sitting as the reference. When issues arise, re-record both clips back-to-back rather than running loudness normalization on an isolated file.

For a script of many lines (a narration), voice every line in one `qwen-clone --lines-file` call rather than one call per line: loading the model and encoding the reference took 8-11 s on Apple Silicon (MPS), paid once instead of per line, and each line then took 2-2.5x its audio length to generate. Transcribe the takes back to check them; you cannot listen to them. Most differences a recogniser reports are homophones or digits and are harmless. A polyphonic Chinese character read with the wrong reading is a real error (重 in 重读 read as *zhòng*); rewrite the text around it (重新读) rather than voicing the same text again. Speaking rate differs between engines: the same 598-character Chinese script took 121 s of speech from Gemini with a medium-pace style and 106 s from Qwen, so measure one take before fixing a script's length to a target duration.

The `response_format` must be configured as `{"type": "audio"}`. Passing `AUDIO` in `response_modalities` will be rejected.

If both `GEMINI_API_KEY` and `GOOGLE_API_KEY` are set, this CLI prioritizes `GEMINI_API_KEY` and sets `both_google_keys_set`. Because the official `google-genai` SDK defaults to `GOOGLE_API_KEY`, check which key is transmitted when alternating between tools.

SDK compatibility note for direct library use: `client.voices` requires `google-genai` version 2.25.0 or newer. It is not available in earlier releases.

## Output

Stdout emits a single JSON object with `command`, `input`, `data`, and `error`. The generated audio path is returned in `data.output` or at the path provided by the caller. Do not consider a clone complete until the output WAV file exists on disk and is playable.
