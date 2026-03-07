import difflib
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


def normalize_text(value):
    return value.strip().lower()


def resolve_session_alias(query, sessions):
    if query in sessions:
        return {"status": "exact", "matched": query}

    query_norm = normalize_text(query)
    normalized = {session: normalize_text(session) for session in sessions}

    starts_with = [s for s, sn in normalized.items() if sn.startswith(query_norm)]
    if len(starts_with) == 1:
        return {"status": "fuzzy", "matched": starts_with[0], "match_type": "prefix"}
    if len(starts_with) > 1:
        return {"status": "ambiguous", "candidates": starts_with}

    contains = [s for s, sn in normalized.items() if query_norm in sn]
    if len(contains) == 1:
        return {"status": "fuzzy", "matched": contains[0], "match_type": "contains"}
    if len(contains) > 1:
        return {"status": "ambiguous", "candidates": contains}

    close = difflib.get_close_matches(query, sessions, n=3, cutoff=0.6)
    if len(close) == 1:
        return {"status": "fuzzy", "matched": close[0], "match_type": "close"}
    if len(close) > 1:
        return {"status": "ambiguous", "candidates": close}

    return {"status": "missing"}


def get_effective_session(sessions):
    saved = get_saved_session_name()
    if saved and saved in sessions:
        return saved, "saved", saved
    if sessions:
        return sessions[0], "auto", saved
    return None, "none", saved


def resolve_target_session(explicit_session=None):
    sessions = discover_sessions()
    if not sessions:
        render_no_session_guide()
        raise RuntimeError(
            "No shared MATLAB session found. Ask user to run matlab.engine.shareEngine in MATLAB."
        )

    if explicit_session:
        resolved = resolve_session_alias(explicit_session, sessions)
        if resolved["status"] == "exact":
            return resolved["matched"], sessions, "explicit"
        if resolved["status"] == "fuzzy":
            matched = resolved["matched"]
            sys.stderr.write(
                f"[INFO] Session '{explicit_session}' matched '{matched}' ({resolved['match_type']}).\n"
            )
            return matched, sessions, "explicit_fuzzy"
        if resolved["status"] == "ambiguous":
            raise RuntimeError(
                f"Session '{explicit_session}' is ambiguous. Candidates: {resolved['candidates']}"
            )
        sys.stderr.write(
            f"[ERROR] Session '{explicit_session}' not found. Available sessions: {sessions}\n"
        )
        raise RuntimeError(f"Session '{explicit_session}' not found.")

    effective, source, saved = get_effective_session(sessions)
    if source == "auto" and saved:
        sys.stderr.write(
            f"[WARN] Saved session '{saved}' is unavailable. Falling back automatically.\n"
        )
    return effective, sessions, source


def connect_to_session(target_name=None):
    target, sessions, source = resolve_target_session(target_name)
    if len(sessions) > 1 and source == "auto":
        sys.stderr.write(
            f"[INFO] Multiple sessions found {sessions}. Connecting to '{target}'.\n"
        )

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
        return {"error": f"Session '{name}' not found.", "sessions": sessions}
    if resolved["status"] == "ambiguous":
        return {
            "error": f"Session '{name}' is ambiguous.",
            "candidates": resolved["candidates"],
            "sessions": sessions,
        }

    selected = resolved["matched"]
    match_type = resolved.get("match_type", "exact")

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
        "match_type": match_type,
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
