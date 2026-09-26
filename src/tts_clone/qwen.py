DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


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


def _looks_chinese(text):
    return any("\u4e00" <= char <= "\u9fff" for char in text)
