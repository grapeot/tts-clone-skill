import base64
import json
import os
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path


API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.8-flash-tts"


def key_source():
    if os.environ.get("GEMINI_API_KEY"):
        return "GEMINI_API_KEY", os.environ["GEMINI_API_KEY"]
    if os.environ.get("GOOGLE_API_KEY"):
        return "GOOGLE_API_KEY", os.environ["GOOGLE_API_KEY"]
    return None, None


def both_keys_set():
    return bool(os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_API_KEY"))


def extract_upstream_message(body):
    text = body if isinstance(body, str) else body.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text[:2000]
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return text[:2000]
    details = error.get("details") or []
    for item in details:
        detail = item.get("detail") if isinstance(item, dict) else ""
        marker = "Original error:"
        if detail and marker in detail:
            return detail.split(marker, 1)[1].strip()[:2000]
    message = error.get("message")
    return (message or text)[:2000]


def _request(url, payload, api_key, timeout, opener=None):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(request, timeout=timeout) as response:
            raw = response.read()
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
        message = extract_upstream_message(raw)
        error = GeminiError(status, message, raw[:2000])
        raise error from exc
    return status, json.loads(raw.decode("utf-8"))


class GeminiError(Exception):
    def __init__(self, status, message, raw):
        super().__init__(message)
        self.status = status
        self.message = message
        self.raw = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")


def _b64_file(path):
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def voice_prefix(value):
    if value.startswith("voicekey_"):
        return "voicekey_"
    if value.startswith("voice_"):
        return "voice_"
    return "unknown"


def replicate(source, consent, out_key, store=False, model=DEFAULT_MODEL, language_code=None, timeout=180, opener=None):
    source_name, api_key = key_source()
    if not api_key:
        raise GeminiError(0, "GEMINI_API_KEY is not set", "")
    payload = {
        "store": bool(store),
        "voice": {
            "model": model,
            "type": "replicated",
            "replicated": {
                "source_audio": {"mime_type": "audio/wav", "data": _b64_file(source)},
                "consent_audio": {"mime_type": "audio/wav", "data": _b64_file(consent)},
            },
        },
    }
    if language_code:
        payload["voice"]["language_code"] = language_code
    _status, body = _request(f"{API_ROOT}/voices", payload, api_key, timeout, opener)
    voice_value = body.get("key") or body.get("id")
    if not voice_value and isinstance(body.get("voice"), dict):
        voice_value = body["voice"].get("key") or body["voice"].get("id")
    if not voice_value:
        raise GeminiError(200, "create voice response had no key or id", json.dumps(list(body.keys())))
    destination = Path(out_key)
    destination.write_text(voice_value)
    destination.chmod(0o600)
    stamp = Path(str(destination) + ".created")
    stamp.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    return {
        "voice_key_file": str(destination),
        "prefix": voice_prefix(voice_value),
        "length": len(voice_value),
        "stored": bool(store),
        "model": model,
        "key_source": source_name,
        "both_google_keys_set": both_keys_set(),
    }


def _audio_bytes(data):
    if data is None:
        return b""
    if isinstance(data, bytes):
        return data
    try:
        return base64.b64decode(data)
    except Exception:
        return b""


def _find_audio(body):
    audio = body.get("output_audio") if isinstance(body, dict) else None
    if isinstance(audio, dict) and audio.get("data"):
        return audio
    for step in body.get("steps") or []:
        for item in step.get("content") or []:
            if item.get("type") == "audio" and item.get("data"):
                return item
    return None


def write_wav(path, raw, sample_rate=24000):
    destination = Path(path)
    if raw[:4] == b"RIFF":
        destination.write_bytes(raw)
        return
    with wave.open(str(destination), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(raw)


def synthesize(voice_key_file, text, out_wav, model=DEFAULT_MODEL, language="zh-CN", style=None, timeout=180, opener=None):
    source_name, api_key = key_source()
    if not api_key:
        raise GeminiError(0, "GEMINI_API_KEY is not set", "")
    voice = Path(voice_key_file).read_text().strip()
    speech = {"voice": voice}
    if language:
        speech["language"] = language
    payload = {
        "model": model,
        "input": text,
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [speech]},
        "store": False,
    }
    if style:
        payload["input"] = [
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                        "annotations": [{"type": "speech_metadata", "style": style}],
                    }
                ],
            }
        ]
    _status, body = _request(f"{API_ROOT}/interactions", payload, api_key, timeout, opener)
    audio = _find_audio(body)
    if not audio:
        raise GeminiError(200, "synthesis response had no audio", json.dumps(list(body.keys()))[:500])
    raw = _audio_bytes(audio.get("data"))
    if not raw:
        raise GeminiError(200, "synthesis audio payload was empty", "")
    write_wav(out_wav, raw, audio.get("sample_rate") or 24000)
    return {
        "output": str(out_wav),
        "bytes": Path(out_wav).stat().st_size,
        "mime_type": audio.get("mime_type"),
        "model": model,
        "key_source": source_name,
        "both_google_keys_set": both_keys_set(),
    }
