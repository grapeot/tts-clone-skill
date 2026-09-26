# Tests

Default tests run entirely offline.

- `inspect` validates synthetic WAV audio and flags reference files shorter than 10 seconds.
- `phrases` returns the two verified consent sentences.
- Tests verify that the Gemini HTTP 500 response wrapper is unwrapped to expose the underlying consent message.
- Mocked voice creation responses ensure the generated key is written to disk rather than echoed to stdout.
- `choose_device` prioritizes hardware in order: CUDA, then MPS, and finally CPU.
- A repository tree scan asserts that no private path markers, password-manager references, or audio fixtures exist in the codebase.

Live Gemini and Qwen executions are handled manually. Never add tests that download model weights or upload audio over the network.
