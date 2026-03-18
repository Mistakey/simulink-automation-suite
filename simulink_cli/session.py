import json
import sys
from pathlib import Path

from simulink_cli.json_io import as_list
from simulink_cli.errors import make_error


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = PLUGIN_ROOT / ".sl_pilot_state.json"


def _get_matlab_engine():
    try:
        import importlib

        return importlib.import_module("matlab.engine")
    except Exception as exc:
        raise RuntimeError("engine_unavailable") from exc


def load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        with STATE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def save_state(state):
    try:
        with STATE_FILE.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=True, indent=2)
    except OSError as exc:
        raise RuntimeError(
            f"Failed to write state file '{STATE_FILE}': {exc}"
        ) from exc


def clear_state():
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
    except OSError as exc:
        raise RuntimeError(
            f"Failed to clear state file '{STATE_FILE}': {exc}"
        ) from exc


def get_saved_session_name():
    state = load_state()
    value = state.get("active_session")
    if isinstance(value, str) and value:
        return value
    return None


def set_saved_session_name(name):
    state = load_state()
    state["active_session"] = name
    save_state(state)


def render_no_session_guide():
    border = "+-----------------------------------------------------------+"
    lines = [
        border,
        "| CRITICAL ERROR: No shared MATLAB session found.          |",
        "| ACTION REQUIRED:                                         |",
        "| 1) Open MATLAB Command Window.                           |",
        "| 2) Run: matlab.engine.shareEngine                        |",
        border,
    ]
    sys.stderr.write("\n" + "\n".join(lines) + "\n\n")


def discover_sessions():
    try:
        engine = _get_matlab_engine()
        return as_list(engine.find_matlab())
    except RuntimeError as exc:
        if str(exc).strip() == "engine_unavailable":
            raise
        raise RuntimeError(f"Failed to discover MATLAB sessions: {exc}")
    except Exception as exc:
        raise RuntimeError(f"Failed to discover MATLAB sessions: {exc}")


def resolve_session_alias(query, sessions):
    if query in sessions:
        return {"status": "exact", "matched": query}
    return {"status": "missing"}


def get_effective_session(sessions):
    saved = get_saved_session_name()
    if len(sessions) == 1:
        return sessions[0], "single", saved
    if sessions:
        return None, "required", saved
    return None, "none", saved


def resolve_target_session(explicit_session=None):
    sessions = discover_sessions()
    if not sessions:
        render_no_session_guide()
        raise RuntimeError("no_session")

    if explicit_session:
        if explicit_session in sessions:
            return explicit_session, sessions, "explicit"
        raise RuntimeError("session_not_found")

    if len(sessions) == 1:
        return sessions[0], sessions, "single"
    raise RuntimeError("session_required")


def connect_to_session(target_name=None):
    target, sessions, source = resolve_target_session(target_name)

    try:
        engine = _get_matlab_engine()
        return engine.connect_matlab(target)
    except Exception as exc:
        raise RuntimeError(f"Failed to connect to MATLAB session '{target}': {exc}")


def safe_connect_to_session(session_name=None):
    """Connect to session, returning (engine, None) or (None, error_dict)."""
    try:
        eng = connect_to_session(session_name)
        return eng, None
    except RuntimeError as exc:
        code = str(exc).strip()
        if code == "engine_unavailable":
            return None, make_error(
                "engine_unavailable",
                "MATLAB Engine for Python is not available.",
                details={"cause": code},
                suggested_fix="Install MATLAB Engine for Python, then retry.",
            )
        if code == "no_session":
            return None, make_error(
                "no_session",
                "No shared MATLAB session found.",
                details={"cause": code},
                suggested_fix="Run matlab.engine.shareEngine in MATLAB, then retry.",
            )
        if code == "session_not_found":
            return None, make_error(
                "session_not_found",
                f"Session '{session_name}' not found.",
                details={"session": session_name, "cause": code},
                suggested_fix="Run `session list` and pass an exact session name.",
            )
        if code == "session_required":
            return None, make_error(
                "session_required",
                "Multiple MATLAB sessions found. Pass --session to disambiguate.",
                details={"cause": code},
                suggested_fix="Run `session list` and pass an exact session name via --session.",
            )
        return None, make_error(
            "runtime_error",
            f"Failed to connect to MATLAB session: {exc}",
            details={"cause": str(exc)},
        )


def command_session_list():
    sessions = discover_sessions()
    effective, source, saved = get_effective_session(sessions)
    return {
        "sessions": sessions,
        "active_session": effective,
        "active_source": source,
        "configured_session": saved,
        "count": len(sessions),
    }


def command_session_use(name):
    sessions = discover_sessions()
    if not sessions:
        render_no_session_guide()
        return make_error(
            "no_session",
            "No shared MATLAB session found.",
            details={"sessions": []},
            suggested_fix="Run matlab.engine.shareEngine in MATLAB, then retry.",
        )
    resolved = resolve_session_alias(name, sessions)
    if resolved["status"] == "missing":
        return make_error(
            "session_not_found",
            f"Session '{name}' not found. Exact session name is required.",
            details={"input": name, "sessions": sessions},
            suggested_fix="Run `session list` and pass an exact session name via --session.",
        )

    selected = resolved["matched"]
    try:
        set_saved_session_name(selected)
    except RuntimeError as exc:
        payload = make_error(
            "state_write_failed",
            str(exc),
            details={"active_session": selected},
            suggested_fix="Check state file permissions and retry `session use`.",
        )
        payload["active_session"] = selected
        return payload
    return {
        "status": "success",
        "active_session": selected,
        "input": name,
        "match_type": "exact",
    }


def command_session_current():
    sessions = discover_sessions()
    effective, source, saved = get_effective_session(sessions)
    return {
        "active_session": effective,
        "active_source": source,
        "configured_session": saved,
        "sessions": sessions,
    }


def command_session_clear():
    try:
        clear_state()
    except RuntimeError as exc:
        return make_error(
            "state_clear_failed",
            str(exc),
            details={},
            suggested_fix="Check state file permissions and retry `session clear`.",
        )
    return {"status": "success", "active_session": None}
