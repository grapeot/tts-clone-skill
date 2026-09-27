import json
import wave

import pytest

from tts_clone.cli import main
from tts_clone.qwen import clone_many, load_lines


class FakeModel:
    def __init__(self):
        self.prompts = 0
        self.calls = []

    def create_voice_clone_prompt(self, ref_audio, ref_text):
        self.prompts += 1
        return {"ref": ref_audio, "text": ref_text}

    def generate_voice_clone(self, text, language, voice_clone_prompt):
        self.calls.append((text, language, voice_clone_prompt["text"]))
        return [[0.0, 0.5, -0.5] * 800], 24000


def test_load_lines_accepts_both_shapes(tmp_path):
    a = tmp_path / "a.json"
    a.write_text(json.dumps([{"id": "s01", "text": "你好"}, {"id": "s02", "text": "hello"}]), encoding="utf-8")
    b = tmp_path / "b.json"
    b.write_text(json.dumps({"segments": [{"id": "s01", "say": "你好", "gap": 0.3}]}), encoding="utf-8")
    assert load_lines(a) == [("s01", "你好"), ("s02", "hello")]
    assert load_lines(b) == [("s01", "你好")]


@pytest.mark.parametrize("rows", [
    [{"id": "../x", "text": "a"}],
    [{"id": "s01", "text": "a"}, {"id": "s01", "text": "b"}],
    [{"id": "s01", "text": "  "}],
    [],
])
def test_load_lines_rejects_unsafe_duplicate_or_empty(tmp_path, rows):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ValueError):
        load_lines(p)


def test_clone_many_loads_once_and_writes_every_line(tmp_path):
    model = FakeModel()
    loads = []

    def loader(model_id, device):
        loads.append((model_id, device))
        return model

    data = clone_many("ref.wav", "参考文本", [("s01", "第一句"), ("s02", "second line")], tmp_path / "out",
                      device="cpu", suffix="_b", loader=loader)
    assert len(loads) == 1 and model.prompts == 1
    assert [c[1] for c in model.calls] == ["Chinese", "Auto"]
    assert data["count"] == 2
    for row in data["outputs"]:
        with wave.open(row["output"], "rb") as handle:
            assert handle.getframerate() == 24000 and handle.getnframes() == 2400
        assert row["output"].endswith(f"{row['id']}_b.wav")
        assert row["audio_seconds"] == 0.1


def test_batch_mode_usage_errors(tmp_path, capsys):
    ref_text = tmp_path / "ref.txt"
    ref_text.write_text("参考", encoding="utf-8")
    code = main(["qwen-clone", "--ref-audio", "ref.wav", "--ref-text-file", str(ref_text),
                 "--lines-file", str(tmp_path / "lines.json")])
    out = json.loads(capsys.readouterr().out)
    assert code == 2 and out["error"]["type"] == "usage"
    code = main(["qwen-clone", "--ref-audio", "ref.wav", "--ref-text-file", str(ref_text),
                 "--text", "x"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2 and "-o is required" in out["error"]["message"]


def test_model_stack_output_never_reaches_stdout(tmp_path, capsys):
    def noisy_loader(model_id, device):
        print("********\nWarning: flash-attn is not installed.\n********")
        return FakeModel()

    clone_many("ref.wav", "参考", [("s01", "一句")], tmp_path, device="cpu", loader=noisy_loader)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "flash-attn" in captured.err
