import time
from pathlib import Path

from tts_clone.audio import inspect_file, prepare_wav

DAY = 24 * 3600
KEY_TTL_DAYS = 7.0
AUDIO_SUFFIXES = (".wav", ".m4a", ".mp3", ".flac", ".aac", ".ogg")


def key_age_days(path):
    stamp = Path(str(path) + ".created")
    if stamp.is_file():
        try:
            return (time.time() - time.mktime(time.strptime(stamp.read_text().strip(), "%Y-%m-%dT%H:%M:%SZ"))) / DAY
        except ValueError:
            return None
    try:
        return (time.time() - path.stat().st_mtime) / DAY
    except OSError:
        return None


def key_is_fresh(path, ttl_days=KEY_TTL_DAYS):
    age = key_age_days(path)
    return age is not None and age <= ttl_days


def find_audio(private_dir, stem):
    base = Path(private_dir)
    for suffix in AUDIO_SUFFIXES:
        candidate = base / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def ensure_wav(private_dir, stem):
    base = Path(private_dir)
    found = find_audio(base, stem)
    if not found:
        return None, None
    if found.suffix == ".wav":
        return found, found
    prepared = base / "prepared"
    destination = prepared / f"{stem}.wav"
    if not destination.is_file() or destination.stat().st_mtime < found.stat().st_mtime:
        prepare_wav(found, destination)
    return destination, found


def resolve(private_dir, now=None):
    base = Path(private_dir)
    key = base / "voicekey.txt"
    if key.is_file() and key_is_fresh(key):
        return {"mode": "voicekey", "key_file": str(key), "age_days": round(key_age_days(key), 2)}
    reference, reference_source = ensure_wav(base, "reference")
    consent, consent_source = ensure_wav(base, "consent")
    if not reference or not consent:
        return {
            "mode": "missing",
            "key_file": str(key),
            "key_fresh": key.is_file() and key_is_fresh(key),
            "missing": [
                stem
                for stem, found in (("reference", reference), ("consent", consent))
                if not found
            ],
        }
    return {
        "mode": "replicate",
        "key_file": str(key),
        "reference": str(reference),
        "consent": str(consent),
        "reference_source": str(reference_source),
        "consent_source": str(consent_source),
    }