import json
import wave
from pathlib import Path

from tts_clone.audio import inspect_file
from tts_clone.cli import main
from tts_clone.gemini import extract_upstream_message, voice_prefix
from tts_clone.phrases import PHRASES
from tts_clone.qwen import choose_device


def _wav(path, seconds, rate=24000):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * int(seconds * rate))


def test_inspect_reference_window(tmp_path):
    good = tmp_path / "ref.wav"
    short = tmp_path / "short.wav"
    _wav(good, 16)
    _wav(short, 8)
    assert inspect_file(good, "reference")["reference_duration_ok"] is True
    assert inspect_file(short, "reference")["reference_duration_ok"] is False
    assert inspect_file(short, "consent")["reference_duration_ok"] is None


def test_phrases_command(capsys):
    code = main(["phrases"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["verified_locales"]["zh-CN"] == PHRASES["zh-CN"]
    assert payload["data"]["verified_locales"]["en-US"].startswith("I am the owner of this voice")


def test_upstream_message_unwraps_wrapped_500():
    body = json.dumps(
        {
            "error": {
                "code": 500,
                "message": "Error translating server response to JSON",
                "details": [
                    {
                        "detail": "INTERNAL: boom\nOriginal error: INVALID_ARGUMENT: Consent flow failed.\nThe recorded phrase didn't match the text on screen."
                    }
                ],
            }
        }
    )
    message = extract_upstream_message(body)
    assert "Consent flow failed" in message
    assert "Error translating server response to JSON" not in message


def test_voice_prefix_does_not_keep_secret_suffix():
    assert voice_prefix("voicekey_SECRET") == "voicekey_"
    assert voice_prefix("voice_abc") == "voice_"


def test_device_choice():
    assert choose_device(True, True) == "cuda:0"
    assert choose_device(False, True) == "mps"
    assert choose_device(False, False) == "cpu"


def test_gemini_replicate_redacts_key(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.wav"
    consent = tmp_path / "consent.wav"
    key_path = tmp_path / "voice.key"
    _wav(source, 12)
    _wav(consent, 6)

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"key": "voicekey_SECRETVALUE"}).encode()

    def opener(request, timeout):
        assert b"SECRET" not in request.data or b"voicekey" not in request.full_url.encode()
        assert any(key.lower() == "x-goog-api-key" for key in request.headers)
        return FakeResponse()

    monkeypatch.setenv("GEMINI_API_KEY", "replace-with-your-gemini-api-key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr("tts_clone.gemini.urllib.request.urlopen", opener)
    # replicate() uses opener argument only when passed. CLI uses default.
    # Call the library path through a tiny shim by patching urlopen, which CLI uses.
    code = main(
        [
            "gemini-replicate",
            "--source",
            str(source),
            "--consent",
            str(consent),
            "--out-key",
            str(key_path),
        ]
    )
    assert code == 0
    stdout = capsys.readouterr().out
    assert "voicekey_SECRETVALUE" not in stdout
    assert key_path.read_text() == "voicekey_SECRETVALUE"
    payload = json.loads(stdout)
    assert payload["data"]["prefix"] == "voicekey_"
