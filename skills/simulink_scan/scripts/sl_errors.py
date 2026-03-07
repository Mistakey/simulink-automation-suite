def make_error(code, message, details=None, suggested_fix=None):
    payload = {
        "error": str(code),
        "message": str(message),
        "details": details if isinstance(details, dict) else {},
    }
    if suggested_fix:
        payload["suggested_fix"] = str(suggested_fix)
    return payload
