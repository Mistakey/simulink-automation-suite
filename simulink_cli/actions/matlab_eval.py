"""matlab_eval action — execute arbitrary MATLAB code and return text output."""

from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_payload_field, validate_text_field
from simulink_cli import matlab_transport
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Execute arbitrary MATLAB code and return captured text output."

FIELDS = {
    "code": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "MATLAB code to execute. Supports multi-line.",
    },
    "timeout": {
        "type": "number",
        "required": False,
        "default": 30,
        "description": "Execution timeout in seconds. Prevents runaway code.",
    },
    "session": {
        "type": "string",
        "required": False,
        "default": None,
        "description": "MATLAB session name override.",
    },
}

ERRORS = [
    "engine_unavailable",
    "no_session",
    "session_not_found",
    "session_required",
    "eval_failed",
    "eval_timeout",
    "runtime_error",
]

_OUTPUT_MAX_CHARS = 50_000


def validate(args):
    """Validate matlab_eval arguments. Returns error dict or None."""
    code = args.get("code")
    if code is None or (isinstance(code, str) and not code):
        return make_error(
            "invalid_input",
            "Field 'code' is required and must not be empty.",
            details={"field": "code"},
        )
    err = validate_matlab_payload_field("code", code, max_len=100_000)
    if err is not None:
        return err
    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err

    timeout = args.get("timeout")
    if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
        return make_error(
            "invalid_input",
            "Field 'timeout' must be a positive number.",
            details={"field": "timeout", "value": timeout},
        )

    return None


def execute(args):
    """Execute matlab_eval: run arbitrary MATLAB code, return captured text."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    code = args["code"]
    timeout = args.get("timeout") or FIELDS["timeout"]["default"]

    try:
        result = matlab_transport.eval_code(eng, code, timeout=timeout)
        output = result.get("value") or ""
        warnings = result.get("warnings", [])
    except TimeoutError:
        return make_error(
            "eval_timeout",
            f"MATLAB code execution timed out after {timeout}s.",
            details={"timeout": timeout},
            suggested_fix="Increase timeout or simplify the code.",
        )
    except Exception as exc:
        return make_error(
            "eval_failed",
            f"MATLAB code execution failed: {exc}",
            details={"cause": str(exc)},
            suggested_fix="Check MATLAB code syntax and referenced variables/functions.",
        )

    truncated = len(output) > _OUTPUT_MAX_CHARS
    response = {
        "action": "matlab_eval",
        "output": output[:_OUTPUT_MAX_CHARS] if truncated else output,
        "truncated": truncated,
        "warnings": warnings,
    }
    if truncated:
        response["total_length"] = len(output)
    return response
