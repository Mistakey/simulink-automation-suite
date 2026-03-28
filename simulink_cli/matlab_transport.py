import io
import sys


def _result(value=None, warnings=None):
    return {
        "value": value,
        "warnings": list(warnings or []),
    }


def _reset_lastwarn(engine):
    if hasattr(engine, "lastwarn"):
        try:
            engine.lastwarn("", "", nargout=0)
            return
        except TypeError:
            pass
        except Exception:
            pass


def _fallback_warning_log(engine):
    try:
        warning_log = getattr(engine, "warning_log")
    except Exception:
        return None
    if isinstance(warning_log, list):
        return warning_log
    return None


def _drain_warnings(engine):
    if hasattr(engine, "lastwarn"):
        try:
            message, warning_id = engine.lastwarn(nargout=2)
            text = str(message).strip()
            if text:
                warning_log = _fallback_warning_log(engine)
                if warning_log is not None:
                    warning_log.clear()
                return [text]
        except TypeError:
            pass
        except Exception:
            pass
    warning_log = _fallback_warning_log(engine)
    if warning_log is not None:
        warnings = list(warning_log)
        warning_log.clear()
        return warnings
    return []


def _should_retry_without_nargout(exc):
    text = str(exc)
    return (
        "nargout" in text
        or "unexpected keyword argument" in text
        or "takes no keyword arguments" in text
        or "positional arguments but" in text
    )


def _attach_exception_warnings(exc, warnings):
    if not warnings:
        return
    existing = list(getattr(exc, "matlab_warnings", []))
    exc.matlab_warnings = existing + list(warnings)


def _call_with_optional_nargout(fn, args, nargout):
    _saved_out = sys.stdout
    _saved_err = sys.stderr
    _buf = io.StringIO()
    sys.stdout = _buf
    sys.stderr = _buf
    try:
        # Attempt 1: full MATLAB Engine kwargs — suppresses MATLAB C-level stdout.
        try:
            return fn(*args, nargout=nargout, stdout=_buf, stderr=_buf)
        except TypeError as exc:
            if not _should_retry_without_nargout(exc):
                raise
        # Attempt 2: without stdout/stderr kwargs (fake/legacy engines).
        # sys.stdout redirect above still suppresses Python-level writes.
        try:
            return fn(*args, nargout=nargout)
        except TypeError as exc:
            if not _should_retry_without_nargout(exc):
                raise
        # Attempt 3: bare call (functions that refuse the nargout keyword).
        return fn(*args)
    finally:
        sys.stdout = _saved_out
        sys.stderr = _saved_err


def call(engine, name, *args, nargout=1):
    _reset_lastwarn(engine)
    fn = getattr(engine, name)
    try:
        value = _call_with_optional_nargout(fn, args, nargout)
    except Exception as exc:
        _attach_exception_warnings(exc, _drain_warnings(engine))
        raise
    warnings = _drain_warnings(engine)
    return _result(value=value, warnings=warnings)


def call_no_output(engine, name, *args):
    _reset_lastwarn(engine)
    fn = getattr(engine, name)
    try:
        _call_with_optional_nargout(fn, args, 0)
    except Exception as exc:
        _attach_exception_warnings(exc, _drain_warnings(engine))
        raise
    warnings = _drain_warnings(engine)
    return _result(value=None, warnings=warnings)


def get_param(engine, target, param):
    return call(engine, "get_param", target, param)


def set_param(engine, target, param, value):
    return call_no_output(engine, "set_param", target, param, value)


def find_system(engine, *args):
    return call(engine, "find_system", *args)


def hilite_system(engine, target):
    return call_no_output(engine, "hilite_system", target)


def bdroot(engine):
    return call(engine, "bdroot")


def new_system(engine, name):
    """Create a new Simulink model. Returns result with model name."""
    return call(engine, "new_system", name)


def open_system(engine, path):
    """Open a Simulink model from file path or MATLAB path."""
    return call_no_output(engine, "open_system", path)


def save_system(engine, model):
    """Save a loaded Simulink model to disk."""
    return call_no_output(engine, "save_system", model)


def load_system(engine, name):
    """Load a Simulink library or model into memory."""
    return call_no_output(engine, "load_system", name)


def add_block(engine, source, dest):
    """Add a library block to a loaded model."""
    return call_no_output(engine, "add_block", source, dest)


def add_line(engine, system, src, dst):
    """Add a signal line connecting two block ports."""
    return call(engine, "add_line", system, src, dst)


def close_system(engine, model):
    """Close a Simulink model. Passes 0 to suppress save dialog."""
    return call_no_output(engine, "close_system", model, 0)


def update_diagram(engine, model):
    """Compile/update a Simulink model diagram."""
    return call_no_output(engine, "set_param", model, "SimulationCommand", "update")


def delete_line(engine, system, src, dst):
    """Delete a signal line between two block ports."""
    return call_no_output(engine, "delete_line", system, src, dst)


def delete_block(engine, block_path):
    """Delete a block from a loaded model."""
    return call_no_output(engine, "delete_block", block_path)


def sim(engine, model):
    """Run simulation on a loaded model."""
    return call(engine, "sim", model)
