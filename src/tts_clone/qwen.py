import contextlib
import sys

DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


def _quiet_stdout():
    """qwen-tts prints a flash-attn banner to stdout on import; the CLI owes callers exactly
    one JSON object there, so everything the model stack prints goes to stderr instead."""
    return contextlib.redirect_stdout(sys.stderr)


def choose_device(has_cuda, has_mps):
    if has_cuda:
        return "cuda:0"
    if has_mps:
        return "mps"
    return "cpu"


def probe_devices():
    try:
        import torch
    except ImportError:
        return False, False
    has_cuda = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
    mps = getattr(torch, "backends", None)
    has_mps = bool(mps and getattr(mps, "mps", None) and torch.backends.mps.is_available())
    return has_cuda, has_mps


def clone(ref_audio, ref_text, text, out_wav, model_id=DEFAULT_MODEL, device=None):
    with _quiet_stdout():
        return _clone(ref_audio, ref_text, text, out_wav, model_id, device)


def _clone(ref_audio, ref_text, text, out_wav, model_id, device):
    try:
        import soundfile as sf
        import torch
        from qwen_tts import Qwen3TTSModel
    except ImportError as exc:
        raise RuntimeError(
            "qwen-tts is not installed. Install the optional extra: uv pip install 'tts-clone-skill[qwen]'"
        ) from exc
    selected = device or choose_device(*probe_devices())
    dtype = torch.bfloat16 if selected != "cpu" else torch.float32
    loaded = Qwen3TTSModel.from_pretrained(
        model_id,
        device_map=selected,
        dtype=dtype,
        attn_implementation="sdpa",
    )
    wavs, sample_rate = loaded.generate_voice_clone(
        text=text,
        language="Chinese" if _looks_chinese(text) else "Auto",
        ref_audio=ref_audio,
        ref_text=ref_text,
    )
    sf.write(out_wav, wavs[0], sample_rate)
    return {
        "output": out_wav,
        "sample_rate": sample_rate,
        "model": model_id,
        "device": selected,
        "attn_implementation": "sdpa",
    }


def load_lines(path):
    """Lines to voice from JSON: ``[{"id", "text"}]`` or ``{"segments": [{"id", "say"}]}``.

    Ids become file names (``<id>.wav``), so they must be unique and path-safe."""
    import json
    import re

    spec = json.loads(open(path, encoding="utf-8").read())
    rows = spec["segments"] if isinstance(spec, dict) else spec
    lines = []
    for n, row in enumerate(rows):
        sid = str(row.get("id", f"{n + 1:02d}"))
        text = str(row.get("text", row.get("say", ""))).strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", sid) or sid.startswith("."):
            raise ValueError(f"line id {sid!r} is not a safe file name")
        if not text:
            raise ValueError(f"line {sid} has no text")
        lines.append((sid, text))
    ids = [sid for sid, _ in lines]
    if len(set(ids)) != len(ids):
        raise ValueError("line ids are not unique")
    if not lines:
        raise ValueError("no lines to voice")
    return lines


def _write_wav(path, samples, sample_rate):
    """16-bit mono WAV; numpy when present (it is, with the qwen extra), stdlib otherwise."""
    import wave

    try:
        import numpy as np

        pcm = (np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
    except ImportError:
        import array
        import sys

        buf = array.array("h", (int(max(-1.0, min(1.0, float(v))) * 32767.0) for v in samples))
        if sys.byteorder == "big":
            buf.byteswap()
        pcm = buf.tobytes()
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(sample_rate))
        handle.writeframes(pcm)


def _load_model(model_id, device):
    try:
        import torch
        from qwen_tts import Qwen3TTSModel
    except ImportError as exc:
        raise RuntimeError(
            "qwen-tts is not installed. Install the optional extra: uv pip install 'tts-clone-skill[qwen]'"
        ) from exc
    dtype = torch.bfloat16 if device != "cpu" else torch.float32
    return Qwen3TTSModel.from_pretrained(model_id, device_map=device, dtype=dtype, attn_implementation="sdpa")


def clone_many(ref_audio, ref_text, lines, out_dir, model_id=DEFAULT_MODEL, device=None, suffix="", loader=None):
    """Voice many lines with one model load and one voice-clone prompt.

    Loading the 1.7B model and encoding the reference cost seconds per call; a
    script of many lines voiced one CLI call at a time pays that for every line.
    ``loader(model_id, device)`` exists for offline tests."""
    with _quiet_stdout():
        return _clone_many(ref_audio, ref_text, lines, out_dir, model_id, device, suffix, loader)


def _clone_many(ref_audio, ref_text, lines, out_dir, model_id, device, suffix, loader):
    import os
    import time

    selected = device or choose_device(*probe_devices())
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    model = (loader or _load_model)(model_id, selected)
    prompt = model.create_voice_clone_prompt(ref_audio=ref_audio, ref_text=ref_text)
    load_seconds = time.time() - t0
    results = []
    for sid, text in lines:
        t1 = time.time()
        wavs, sample_rate = model.generate_voice_clone(
            text=text,
            language="Chinese" if _looks_chinese(text) else "Auto",
            voice_clone_prompt=prompt,
        )
        out = os.path.join(out_dir, f"{sid}{suffix}.wav")
        _write_wav(out, wavs[0], sample_rate)
        results.append({
            "id": sid,
            "output": out,
            "audio_seconds": round(len(wavs[0]) / sample_rate, 3),
            "compute_seconds": round(time.time() - t1, 3),
        })
    return {
        "outputs": results,
        "count": len(results),
        "load_seconds": round(load_seconds, 3),
        "model": model_id,
        "device": selected,
        "attn_implementation": "sdpa",
    }


def _looks_chinese(text):
    return any("\u4e00" <= char <= "\u9fff" for char in text)
