import json
import sys


def emit(payload, code=0):
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return code


def ok(command, payload_input, data):
    return emit(
        {"command": command, "input": payload_input, "data": data, "error": None},
        0,
    )


def fail(command, payload_input, error_type, message, code, **extra):
    error = {"type": error_type, "message": message}
    error.update(extra)
    return emit(
        {"command": command, "input": payload_input, "data": None, "error": error},
        code,
    )
