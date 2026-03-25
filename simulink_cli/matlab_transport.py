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
    try:
        return fn(*args, nargout=nargout)
    except TypeError as exc:
        if not _should_retry_without_nargout(exc):
            raise
    return fn(*args)


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


def add_block(engine, source, dest):
    """Add a library block to a loaded model."""
    return call_no_output(engine, "add_block", source, dest)
