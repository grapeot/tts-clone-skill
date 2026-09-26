import shutil
import subprocess
import wave
from pathlib import Path


REFERENCE_MIN_SECONDS = 10.0
REFERENCE_MAX_SECONDS = 30.0


def wav_duration(path):
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate()
        channels = handle.getnchannels()
        width = handle.getsampwidth()
    if rate <= 0:
        raise ValueError("wav sample rate is zero")
    return {
        "duration_seconds": frames / float(rate),
        "sample_rate": rate,
        "channels": channels,
        "sample_width_bytes": width,
        "codec": "pcm",
    }


def ffprobe_duration(path):
    binary = shutil.which("ffprobe")
    if not binary:
        raise FileNotFoundError("ffprobe not found")
    result = subprocess.run(
        [
            binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-show_entries",
            "stream=codec_name,sample_rate,channels",
            "-of",
            "default=nw=1",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    info = {"duration_seconds": None, "sample_rate": None, "channels": None, "codec": None}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == "duration" and value:
            info["duration_seconds"] = float(value)
        elif key == "sample_rate" and value:
            info["sample_rate"] = int(value)
        elif key == "channels" and value:
            info["channels"] = int(value)
        elif key == "codec_name":
            info["codec"] = value
    if info["duration_seconds"] is None:
        raise RuntimeError("ffprobe did not return a duration")
    return info


def inspect_file(path, role):
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(str(target))
    if target.suffix.lower() == ".wav":
        info = wav_duration(target)
    else:
        info = ffprobe_duration(target)
    duration = info["duration_seconds"]
    reference_ok = REFERENCE_MIN_SECONDS <= duration <= REFERENCE_MAX_SECONDS
    return {
        "path": str(target),
        "role": role,
        "duration_seconds": round(duration, 3),
        "sample_rate": info.get("sample_rate"),
        "channels": info.get("channels"),
        "codec": info.get("codec"),
        "reference_window_seconds": [REFERENCE_MIN_SECONDS, REFERENCE_MAX_SECONDS],
        "reference_duration_ok": reference_ok if role == "reference" else None,
    }


def prepare_wav(source, destination):
    binary = shutil.which("ffmpeg")
    if not binary:
        raise FileNotFoundError("ffmpeg not found")
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            binary,
            "-y",
            "-i",
            str(source),
            "-ar",
            "24000",
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            str(dest),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")
    return dest
