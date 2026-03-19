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


def call(engine, name, *args, nargout=1):
    _reset_lastwarn(engine)
    fn = getattr(engine, name)
    try:
        value = fn(*args, nargout=nargout)
    except TypeError:
        value = fn(*args)
    warnings = _drain_warnings(engine)
    return _result(value=value, warnings=warnings)


def call_no_output(engine, name, *args):
    _reset_lastwarn(engine)
    fn = getattr(engine, name)
    try:
        fn(*args, nargout=0)
    except TypeError:
        fn(*args)
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
