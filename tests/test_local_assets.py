import json
import wave
from pathlib import Path

from tts_clone.local_assets import key_is_fresh, resolve
from tts_clone.cli import main


def _wav(path, seconds, rate=24000):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * int(seconds * rate))


def test_voicekey_age_uses_created_stamp(tmp_path):
    key = tmp_path / "voicekey.txt"
    key.write_text("voicekey_x")
    stamp = Path(str(key) + ".created")
    import time

    stamp.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 2 * 86400)))
    assert key_is_fresh(key)
    stamp.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 8 * 86400)))
    assert not key_is_fresh(key)


def test_resolve_prefers_fresh_key(tmp_path):
    key = tmp_path / "voicekey.txt"
    key.write_text("voicekey_x")
    stamp = Path(str(key) + ".created")
    import time

    stamp.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 86400)))
    data = resolve(tmp_path)
    assert data["mode"] == "voicekey"
    assert "voicekey_x" not in json.dumps(data)


def test_resolve_falls_back_to_m4a_prepared_wav(tmp_path):
    import shutil

    if not shutil.which("ffmpeg"):
        import pytest

        pytest.skip("ffmpeg not installed")
    m4a = tmp_path / "reference.m4a"
    _wav(tmp_path / "seed.wav", 1)
    import subprocess

    subprocess.run(
        [shutil.which("ffmpeg"), "-y", "-i", str(tmp_path / "seed.wav"), str(m4a)],
        check=True,
        capture_output=True,
    )
    (tmp_path / "consent.wav").write_bytes(b"")
    data = resolve(tmp_path)
    assert data["mode"] == "replicate"
    assert data["reference"].endswith("prepared/reference.wav")
    assert data["consent"].endswith("consent.wav")
    assert data["reference_source"].endswith("reference.m4a")


def test_resolve_reports_missing(tmp_path):
    data = resolve(tmp_path)
    assert data["mode"] == "missing"
    assert sorted(data["missing"]) == ["consent", "reference"]


def test_speak_missing_reports_names(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "replace-with-your-gemini-api-key")
    code = main(["gemini-speak", "--text", "hello", "-o", "out.wav"])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["type"] == "usage"