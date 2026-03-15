import argparse
import json


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def emit_json(payload):
    print(json.dumps(payload, ensure_ascii=True, default=str))


def as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def project_top_level_fields(payload, fields):
    if not isinstance(fields, list) or not fields:
        return payload
    return {key: value for key, value in payload.items() if key in fields}
