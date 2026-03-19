from simulink_cli.errors import make_error


def _invalid_input(field_name, message):
    return make_error(
        "invalid_input",
        f"Field '{field_name}' {message}.",
        details={"field": field_name},
    )


def _validate_string_field(
    field_name,
    value,
    max_len=256,
    reserved_chars=(),
    allow_control_chars=False,
    reject_surrounding_whitespace=False,
    allow_empty=False,
):
    if value is None:
        return None

    text = str(value)
    if not text and not allow_empty:
        return _invalid_input(field_name, "must not be empty")
    if reject_surrounding_whitespace and text != text.strip():
        return _invalid_input(field_name, "has leading/trailing whitespace")
    if len(text) > max_len:
        return _invalid_input(field_name, f"exceeds max length {max_len}")
    if "\x00" in text:
        return _invalid_input(field_name, "contains control characters")
    if not allow_control_chars and any(ord(char) < 32 for char in text):
        return _invalid_input(field_name, "contains control characters")
    if reserved_chars and any(char in text for char in reserved_chars):
        return _invalid_input(field_name, "contains reserved characters")
    return None


def validate_session_field(field_name, value, max_len=256):
    return _validate_string_field(
        field_name,
        value,
        max_len=max_len,
        reserved_chars=("?", "#", "%"),
        reject_surrounding_whitespace=True,
    )


def validate_matlab_name_field(field_name, value, max_len=256):
    return _validate_string_field(
        field_name,
        value,
        max_len=max_len,
        reserved_chars=(),
        allow_control_chars=True,
    )


def validate_matlab_payload_field(field_name, value, max_len=256):
    return _validate_string_field(
        field_name,
        value,
        max_len=max_len,
        reserved_chars=(),
        allow_control_chars=True,
        allow_empty=True,
    )


def validate_text_field(field_name, value, max_len=256):
    return validate_session_field(field_name, value, max_len=max_len)


def validate_value_field(field_name, value, max_len=256):
    return validate_matlab_payload_field(field_name, value, max_len=max_len)


def validate_json_type(action, field_name, value, field_meta):
    """Validate JSON field type matches schema. Shared across skills."""
    if value is None:
        return
    field_type = field_meta.get("type")
    if field_type == "boolean" and not isinstance(value, bool):
        raise ValueError(
            f"invalid_json: field '{field_name}' for action '{action}' must be boolean"
        )
    if field_type == "string" and not isinstance(value, str):
        raise ValueError(
            f"invalid_json: field '{field_name}' for action '{action}' must be string"
        )
    if field_type == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
        raise ValueError(
            f"invalid_json: field '{field_name}' for action '{action}' must be integer"
        )
    if field_type == "array":
        if not isinstance(value, list):
            raise ValueError(
                f"invalid_json: field '{field_name}' for action '{action}' must be an array"
            )
        if field_meta.get("items") == "string" and not all(
            isinstance(item, str) for item in value
        ):
            raise ValueError(
                f"invalid_json: field '{field_name}' for action '{action}' must be an array of strings"
            )
