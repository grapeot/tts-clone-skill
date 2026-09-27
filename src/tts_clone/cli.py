import argparse
import sys

from tts_clone.audio import inspect_file, prepare_wav
from tts_clone.envelope import fail, ok
from tts_clone.gemini import GeminiError, replicate, synthesize
from tts_clone.local_assets import resolve
from tts_clone.phrases import DOCS_URL, PHRASES
from tts_clone.qwen import DEFAULT_MODEL, clone


def _public_input(args):
    data = vars(args).copy()
    data.pop("func", None)
    return {key: value for key, value in data.items() if value is not None}


def cmd_phrases(args):
    return ok(
        "phrases",
        _public_input(args),
        {
            "docs_url": DOCS_URL,
            "verified_locales": PHRASES,
            "locale_count_on_docs": 30,
        },
    )


def cmd_inspect(args):
    try:
        data = inspect_file(args.path, args.role)
    except FileNotFoundError as exc:
        return fail("inspect", _public_input(args), "not_found", str(exc), 2)
    except Exception as exc:
        return fail("inspect", _public_input(args), "inspect_failed", str(exc), 2)
    return ok("inspect", _public_input(args), data)


def cmd_prepare(args):
    try:
        destination = prepare_wav(args.input, args.output)
        data = inspect_file(destination, args.role)
        data["output"] = str(destination)
    except FileNotFoundError as exc:
        return fail("prepare", _public_input(args), "not_found", str(exc), 2)
    except Exception as exc:
        return fail("prepare", _public_input(args), "prepare_failed", str(exc), 2)
    return ok("prepare", _public_input(args), data)


def cmd_gemini_replicate(args):
    try:
        data = replicate(
            args.source,
            args.consent,
            args.out_key,
            store=args.store,
            model=args.model,
            language_code=args.language_code,
        )
    except GeminiError as exc:
        code = 10 if exc.status in (0, 401, 403) else 12 if exc.status in (400, 500) else 13
        return fail(
            "gemini-replicate",
            _public_input(args),
            "gemini_error",
            exc.message,
            code,
            http_status=exc.status,
        )
    return ok("gemini-replicate", _public_input(args), data)


def cmd_gemini_speak(args):
    text = args.text
    if args.text_file:
        text = open(args.text_file, encoding="utf-8").read().strip()
    if not text:
        return fail("gemini-speak", _public_input(args), "usage", "text is empty", 2)
    key_file = args.voice_key_file
    fallback = None
    if not key_file:
        fallback = resolve(args.private_dir)
        if fallback["mode"] == "missing":
            return fail(
                "gemini-speak",
                _public_input(args),
                "usage",
                "no voice key and private dir missing " + ",".join(fallback["missing"]),
                2,
                private_dir=str(args.private_dir),
            )
        if fallback["mode"] == "replicate":
            try:
                replicate(
                    fallback["reference"],
                    fallback["consent"],
                    fallback["key_file"],
                    model=args.model,
                )
                fallback = resolve(args.private_dir)
            except GeminiError as exc:
                code = 10 if exc.status in (0, 401, 403) else 12 if exc.status in (400, 500) else 13
                return fail(
                    "gemini-speak",
                    _public_input(args),
                    "gemini_error",
                    exc.message,
                    code,
                    http_status=exc.status,
                )
        key_file = fallback["key_file"]
    try:
        data = synthesize(
            key_file,
            text,
            args.output,
            model=args.model,
            language=args.language,
            style=args.style,
        )
    except GeminiError as exc:
        code = 10 if exc.status in (0, 401, 403) else 12 if exc.status in (400, 500) else 13
        return fail(
            "gemini-speak",
            _public_input(args),
            "gemini_error",
            exc.message,
            code,
            http_status=exc.status,
        )
    if fallback is not None:
        data["voice_key_source"] = fallback["mode"]
    return ok("gemini-speak", _public_input(args), data)


def cmd_qwen_clone(args):
    text = args.text
    if args.text_file:
        text = open(args.text_file, encoding="utf-8").read().strip()
    ref_text = open(args.ref_text_file, encoding="utf-8").read().strip()
    if not text or not ref_text:
        return fail("qwen-clone", _public_input(args), "usage", "text or ref text is empty", 2)
    try:
        data = clone(args.ref_audio, ref_text, text, args.output, model_id=args.model, device=args.device)
    except Exception as exc:
        return fail("qwen-clone", _public_input(args), "qwen_error", str(exc), 2)
    return ok("qwen-clone", _public_input(args), data)


def build_parser():
    parser = argparse.ArgumentParser(prog="tts-clone")
    sub = parser.add_subparsers(dest="command", required=True)

    phrases = sub.add_parser("phrases")
    phrases.set_defaults(func=cmd_phrases)

    inspect = sub.add_parser("inspect")
    inspect.add_argument("path")
    inspect.add_argument("--role", choices=["reference", "consent"], required=True)
    inspect.set_defaults(func=cmd_inspect)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("input")
    prepare.add_argument("-o", "--output", required=True)
    prepare.add_argument("--role", choices=["reference", "consent"], default="reference")
    prepare.set_defaults(func=cmd_prepare)

    replicate_cmd = sub.add_parser("gemini-replicate")
    replicate_cmd.add_argument("--source", required=True)
    replicate_cmd.add_argument("--consent", required=True)
    replicate_cmd.add_argument("--out-key", required=True)
    replicate_cmd.add_argument("--store", action="store_true")
    replicate_cmd.add_argument("--model", default="gemini-3.8-flash-tts")
    replicate_cmd.add_argument("--language-code")
    replicate_cmd.set_defaults(func=cmd_gemini_replicate)

    speak = sub.add_parser("gemini-speak")
    speak.add_argument("--voice-key-file")
    speak.add_argument("--private-dir", default="private")
    speak.add_argument("--text")
    speak.add_argument("--text-file")
    speak.add_argument("-o", "--output", required=True)
    speak.add_argument("--model", default="gemini-3.8-flash-tts")
    speak.add_argument("--language", default="zh-CN")
    speak.add_argument("--style")
    speak.set_defaults(func=cmd_gemini_speak)

    qwen = sub.add_parser("qwen-clone")
    qwen.add_argument("--ref-audio", required=True)
    qwen.add_argument("--ref-text-file", required=True)
    qwen.add_argument("--text")
    qwen.add_argument("--text-file")
    qwen.add_argument("-o", "--output", required=True)
    qwen.add_argument("--model", default=DEFAULT_MODEL)
    qwen.add_argument("--device")
    qwen.set_defaults(func=cmd_qwen_clone)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
