# PRD

## User

An autonomous agent, or a person directing an agent, who needs a short synthesized reading of provided text using an authorized voice clone.

## Job

Convert two local audio recordings into a cloned voice—using either Gemini voice replication or local Qwen3-TTS inference—and write a new line of speech to a WAV file, or every line of a multi-line script (a video narration) to one WAV per line.

## Success

- The package installs cleanly without requiring private paths, hardcoded credentials, or bundled voice samples.
- Gemini replication fails closed if the consent sentence or speaker verification check fails, returning the upstream error message rather than only the generic HTTP 500 wrapper.
- Voice secrets are saved directly to disk and never printed to stdout.
- The workflow supports passing the same reference audio and synthesis text to Qwen for listening comparisons.
- Offline tests pass without network connectivity or downloaded model weights.
- A multi-line script voiced with Qwen loads the model and encodes the reference once, writes `<id>.wav` per line, and reports per-line audio and compute seconds.
- Stdout carries exactly one JSON object even when the model stack prints banners or warnings.

## Non-goals

- Training or fine-tuning new model checkpoints.
- Distributing sample or demo voices.
- Invoking live APIs during continuous integration runs.
- Replacing Google AI Studio as an in-browser audio recorder.
