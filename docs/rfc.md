# RFC

## Engines

Gemini voice replication combines a remote voice creation request with a subsequent synthesis call. The underlying model remains `gemini-3.8-flash-tts`. The caller's cloned voice is referenced by a `voicekey_` or `voice_` handle rather than a new model ID.

Qwen3-TTS cloning runs entirely through local inference using `Qwen/Qwen3-TTS-12Hz-1.7B-Base`. It requires a reference audio recording alongside a verbatim transcript of that clip.

## CLI

The public interface is `python -m tts_clone`. The Gemini integration relies exclusively on the standard library so the base installation avoids PyTorch dependencies. Qwen imports are deferred until the clone function is called.

The `prepare` command invokes ffmpeg to output 24 kHz mono 16-bit WAV files. The `inspect` command reads WAV headers directly, using ffprobe for other container formats.

Gemini HTTP communication uses `urllib` to call `https://generativelanguage.googleapis.com/v1beta/voices` and `/interactions`. The API key is passed in the `x-goog-api-key` header. Speech synthesis specifies `response_format.type = audio` rather than `response_modalities: ["AUDIO"]`.

## Secrets

Voice handles are written only to the destination file specified by `--out-key`. Emitted JSON may include metadata such as the `voicekey_` or `voice_` prefix, key length, and file path, but must never expose the raw handle.

## Failure mapping

Missing credentials, as well as HTTP 401 and 403 errors, produce exit code 10. HTTP 400 and 500 responses from the voice endpoint map to exit code 12, reflecting a live finding on 2026-09-26 where an upstream consent rejection arrived inside a 500 wrapper. All other HTTP errors return exit code 13. Error reporting extracts the nested `Original error` instead of displaying `Error translating server response to JSON`.
