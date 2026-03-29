"""model_copy action — copy a loaded Simulink model to a new file."""

from simulink_cli import matlab_transport
from simulink_cli.errors import make_error
from simulink_cli.validation import validate_matlab_name_field, validate_text_field
from simulink_cli.session import safe_connect_to_session

DESCRIPTION = "Copy a loaded Simulink model to a new file path."

FIELDS = {
    "source": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Name of the loaded source model to copy.",
    },
    "dest": {
        "type": "string",
        "required": True,
        "default": None,
        "description": "Destination file path for the copy (e.g. 'FOC_Basic' or 'C:/models/FOC_v2.slx').",
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
    "model_not_found",
    "model_copy_failed",
    "runtime_error",
]


def validate(args):
    """Validate model_copy arguments. Returns error dict or None."""
    err = validate_matlab_name_field("source", args.get("source"))
    if err is not None:
        return err
    err = validate_text_field("dest", args.get("dest"))
    if err is not None:
        return err
    err = validate_text_field("session", args.get("session"))
    if err is not None:
        return err

    source = args.get("source")
    if source is None or (isinstance(source, str) and not source):
        return make_error(
            "invalid_input",
            "Field 'source' is required.",
            details={"field": "source"},
        )
    dest = args.get("dest")
    if dest is None or (isinstance(dest, str) and not dest):
        return make_error(
            "invalid_input",
            "Field 'dest' is required.",
            details={"field": "dest"},
        )
    return None


def execute(args):
    """Execute model_copy: save a loaded model to a new file path."""
    eng, err = safe_connect_to_session(args.get("session"))
    if err is not None:
        return err

    source = args["source"]
    dest = args["dest"]

    # Precondition: source model is loaded
    try:
        matlab_transport.get_param(eng, source, "Handle")
    except Exception:
        return make_error(
            "model_not_found",
            f"Source model '{source}' is not loaded.",
            details={"source": source},
            suggested_fix="Open or create the source model first with model_open or model_new.",
        )

    # Execute copy via file-level copyfile (avoids save_system rename side-effect)
    dest_escaped = dest.replace("'", "''")
    copy_code = (
        f"save_system('{source}'); "
        f"srcFile = get_param('{source}', 'FileName'); "
        f"destFile = '{dest_escaped}'; "
        f"if ~endsWith(destFile, '.slx'), destFile = [destFile '.slx']; end; "
        f"copyfile(srcFile, destFile);"
    )
    try:
        matlab_transport.eval_code(eng, copy_code, timeout=30)
    except Exception as exc:
        return make_error(
            "model_copy_failed",
            f"Failed to copy model '{source}' to '{dest}'.",
            details={"source": source, "dest": dest, "cause": str(exc)},
            suggested_fix="Check the destination path for write permissions and valid file name.",
        )

    # Verify source model is still loaded (not renamed)
    try:
        matlab_transport.get_param(eng, source, "Handle")
    except Exception:
        return make_error(
            "model_copy_failed",
            f"Copy succeeded but source model '{source}' is no longer loaded.",
            details={"source": source, "dest": dest},
        )

    return {
        "action": "model_copy",
        "source": source,
        "dest": dest,
    }
