import json
import sys
from pathlib import Path

from .sl_common import as_list


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
STATE_FILE = PLUGIN_ROOT / ".sl_pilot_state.json"


def _get_matlab_engine():
    try:
        import importlib

        return importlib.import_module("matlab.engine")
    except Exception as exc:
        raise RuntimeError(
            "MATLAB Engine for Python is not available. Install/configure matlab.engine in this Python environment."
        ) from exc


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
    except Exception as exc:
        raise RuntimeError(f"Failed to discover MATLAB sessions: {exc}")


def resolve_session_alias(query, sessions):
    if query in sessions:
        return {"status": "exact", "matched": query}
    return {"status": "missing"}


def get_effective_session(sessions):
    saved = get_saved_session_name()
    if saved and saved in sessions:
        return saved, "saved", saved
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
        return {
            "error": "No shared MATLAB session found. Ask user to run matlab.engine.shareEngine in MATLAB."
        }
    resolved = resolve_session_alias(name, sessions)
    if resolved["status"] == "missing":
        return {
            "error": "session_not_found",
            "message": f"Session '{name}' not found. Exact session name is required.",
            "sessions": sessions,
        }

    selected = resolved["matched"]
    try:
        set_saved_session_name(selected)
    except RuntimeError as exc:
        return {
            "error": "state_write_failed",
            "message": str(exc),
            "active_session": selected,
        }
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
        return {"error": "state_clear_failed", "message": str(exc)}
    return {"status": "success", "active_session": None}
