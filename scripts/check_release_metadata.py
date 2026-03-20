from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


SEMVER_RE = re.compile(r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")


class ReleaseMetadataError(RuntimeError):
    """Raised when release metadata is inconsistent."""


@dataclass(frozen=True)
class ReleaseMetadata:
    plugin_name: str
    plugin_version: str
    marketplace_version: str
    schema_version: str
    expected_schema_version: str
    tag: str | None = None


def normalize_version(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("refs/tags/"):
        normalized = normalized.removeprefix("refs/tags/")
    if normalized.startswith("v"):
        normalized = normalized[1:]
    if not SEMVER_RE.fullmatch(normalized):
        raise ReleaseMetadataError(
            f"Expected a semantic version like 2.0.1 or tag v2.0.1, got: {value}"
        )
    return normalized


def parse_semver(version: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(version)
    if not match:
        raise ReleaseMetadataError(f"Invalid semantic version: {version}")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReleaseMetadataError(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseMetadataError(f"Invalid JSON in {path}: {exc}") from exc


def extract_schema_version(core_path: Path) -> str:
    source = core_path.read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(core_path))

    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "build_schema_payload":
            version = _find_version_literal(node)
            if version:
                return version
            break
    raise ReleaseMetadataError(
        f"Could not extract schema version literal from {core_path}"
    )


def _find_version_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == "version":
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value
            nested = _find_version_literal(value)
            if nested:
                return nested
        return None
    if isinstance(node, ast.Return):
        return _find_version_literal(node.value)
    for child in ast.iter_child_nodes(node):
        nested = _find_version_literal(child)
        if nested:
            return nested
    return None


def validate_release_metadata(
    repo_root: Path, expected_tag: str | None = None
) -> ReleaseMetadata:
    plugin_path = repo_root / ".claude-plugin" / "plugin.json"
    marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
    core_path = repo_root / "simulink_cli" / "core.py"

    plugin_manifest = load_json(plugin_path)
    marketplace_manifest = load_json(marketplace_path)

    plugin_name = plugin_manifest.get("name")
    if not isinstance(plugin_name, str) or not plugin_name:
        raise ReleaseMetadataError(f"{plugin_path} is missing a valid plugin name")

    plugin_version = normalize_version(str(plugin_manifest.get("version", "")).strip())
    plugin_major, plugin_minor, _ = parse_semver(plugin_version)
    expected_schema_version = f"{plugin_major}.{plugin_minor}"

    plugins = marketplace_manifest.get("plugins")
    if not isinstance(plugins, list):
        raise ReleaseMetadataError(f"{marketplace_path} is missing a valid plugins list")

    matched = [
        item for item in plugins if isinstance(item, dict) and item.get("name") == plugin_name
    ]
    if len(matched) != 1:
        raise ReleaseMetadataError(
            f"{marketplace_path} must contain exactly one plugin entry named {plugin_name}"
        )

    marketplace_version = normalize_version(str(matched[0].get("version", "")).strip())
    if marketplace_version != plugin_version:
        raise ReleaseMetadataError(
            "Plugin manifest version and marketplace manifest version differ: "
            f"{plugin_version} != {marketplace_version}"
        )

    schema_version = extract_schema_version(core_path)
    if schema_version != expected_schema_version:
        raise ReleaseMetadataError(
            "Schema version must match plugin major.minor: "
            f"expected {expected_schema_version}, found {schema_version}"
        )

    if expected_tag is not None:
        normalized_tag = normalize_version(expected_tag)
        if normalized_tag != plugin_version:
            raise ReleaseMetadataError(
                f"Release tag {expected_tag} does not match plugin version {plugin_version}"
            )
    else:
        normalized_tag = None

    return ReleaseMetadata(
        plugin_name=plugin_name,
        plugin_version=plugin_version,
        marketplace_version=marketplace_version,
        schema_version=schema_version,
        expected_schema_version=expected_schema_version,
        tag=f"v{normalized_tag}" if normalized_tag else None,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate release metadata consistency across manifests and schema."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to inspect.",
    )
    parser.add_argument(
        "--tag",
        help="Expected release tag, for example v2.0.1. Optional for local checks.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        metadata = validate_release_metadata(args.repo_root, expected_tag=args.tag)
    except ReleaseMetadataError as exc:
        print(f"release metadata check failed: {exc}", file=sys.stderr)
        return 1

    print("release metadata check passed")
    print(f"plugin: {metadata.plugin_name}")
    print(f"plugin version: {metadata.plugin_version}")
    print(f"marketplace version: {metadata.marketplace_version}")
    print(f"schema version: {metadata.schema_version}")
    if metadata.tag:
        print(f"tag: {metadata.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
