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


def _drain_warnings(engine):
    if hasattr(engine, "lastwarn"):
        try:
            message, warning_id = engine.lastwarn(nargout=2)
            text = str(message).strip()
            if text:
                if hasattr(engine, "warning_log"):
                    engine.warning_log.clear()
                return [text]
        except TypeError:
            pass
        except Exception:
            pass
    if hasattr(engine, "warning_log"):
        warnings = list(engine.warning_log)
        engine.warning_log.clear()
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
