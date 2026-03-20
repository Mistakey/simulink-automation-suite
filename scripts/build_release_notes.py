from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
import re


SEMVER_RE = re.compile(r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$")


class ReleaseNotesError(RuntimeError):
    """Raised when release notes cannot be built deterministically."""


@dataclass(frozen=True)
class ReleaseCommit:
    full_sha: str
    short_sha: str
    subject: str


@dataclass(frozen=True)
class ReleaseNotesResult:
    version: str
    tag: str
    body: str
    source_kind: str
    source_path: Path | None
    previous_tag: str | None
    commit_count: int


def normalize_version(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("refs/tags/"):
        normalized = normalized.removeprefix("refs/tags/")
    if normalized.startswith("v"):
        normalized = normalized[1:]
    if not SEMVER_RE.fullmatch(normalized):
        raise ReleaseNotesError(f"Expected version like 2.0.1 or tag v2.0.1, got: {value}")
    return normalized


def parse_version_tuple(version: str) -> tuple[int, int, int]:
    normalized = normalize_version(version)
    major, minor, patch = normalized.split(".")
    return int(major), int(minor), int(patch)


def find_release_document(repo_root: Path, version: str) -> Path | None:
    release_dir = repo_root / "docs" / "release"
    if not release_dir.exists():
        return None

    normalized = normalize_version(version)
    patterns = [
        re.compile(rf"(^|[^0-9A-Za-z])v{re.escape(normalized)}([^0-9A-Za-z]|$)", re.IGNORECASE),
        re.compile(rf"(^|[^0-9A-Za-z]){re.escape(normalized)}([^0-9A-Za-z]|$)", re.IGNORECASE),
    ]

    matches: list[Path] = []
    for path in sorted(release_dir.glob("*.md")):
        stem = path.stem
        if any(pattern.search(stem) for pattern in patterns):
            matches.append(path)

    if len(matches) > 1:
        candidates = ", ".join(path.name for path in matches)
        raise ReleaseNotesError(
            f"Multiple release documents match v{normalized}: {candidates}"
        )
    if not matches:
        return None
    return matches[0]


def build_release_notes(
    repo_root: Path, *, version: str, tag: str | None = None, ref: str = "HEAD"
) -> ReleaseNotesResult:
    normalized_version = normalize_version(version)
    normalized_tag = f"v{normalized_version}" if tag is None else f"v{normalize_version(tag)}"
    release_doc = find_release_document(repo_root, normalized_version)
    if release_doc is not None:
        return ReleaseNotesResult(
            version=normalized_version,
            tag=normalized_tag,
            body=release_doc.read_text(encoding="utf-8"),
            source_kind="document",
            source_path=release_doc,
            previous_tag=None,
            commit_count=0,
        )

    previous_tag = find_previous_release_tag(repo_root, normalized_version)
    release_date = git_stdout(repo_root, "show", "-s", "--format=%cs", ref).strip()
    commits = collect_release_commits(repo_root, ref=ref, previous_tag=previous_tag)
    body = render_fallback_release_notes(
        version=normalized_version,
        tag=normalized_tag,
        release_date=release_date,
        previous_tag=previous_tag,
        commits=commits,
    )
    return ReleaseNotesResult(
        version=normalized_version,
        tag=normalized_tag,
        body=body,
        source_kind="generated",
        source_path=None,
        previous_tag=previous_tag,
        commit_count=len(commits),
    )


def find_previous_release_tag(repo_root: Path, version: str) -> str | None:
    current = parse_version_tuple(version)
    tags = [
        tag.strip()
        for tag in git_stdout(repo_root, "tag", "--list", "v*.*.*").splitlines()
        if tag.strip()
    ]
    candidates = []
    for tag in tags:
        try:
            parsed = parse_version_tuple(tag)
        except ReleaseNotesError:
            continue
        if parsed < current:
            candidates.append((parsed, tag))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def collect_release_commits(
    repo_root: Path, *, ref: str, previous_tag: str | None
) -> list[ReleaseCommit]:
    revspec = ref if previous_tag is None else f"{previous_tag}..{ref}"
    output = git_stdout(
        repo_root,
        "log",
        "--reverse",
        "--format=%H%x1f%h%x1f%s",
        revspec,
    )
    commits: list[ReleaseCommit] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        full_sha, short_sha, subject = line.split("\x1f", 2)
        commits.append(
            ReleaseCommit(full_sha=full_sha, short_sha=short_sha, subject=subject)
        )
    return commits


def render_fallback_release_notes(
    *,
    version: str,
    tag: str,
    release_date: str,
    previous_tag: str | None,
    commits: list[ReleaseCommit],
) -> str:
    summary_scope = (
        f"{len(commits)} commits since {previous_tag}"
        if previous_tag
        else f"{len(commits)} commits from repository start"
    )
    highlight_lines = (
        [f"- `{commit.short_sha}` {commit.subject}" for commit in commits]
        if commits
        else ["- No commits were found for this release range."]
    )
    upgrade_lines = [
        f"- Release tag: `{tag}`.",
        f"- Expected schema version: `{version.rsplit('.', 1)[0]}`.",
        f"- Previous semver tag: `{previous_tag}`." if previous_tag else "- Previous semver tag: none (initial release range).",
        "- No curated release document was found under `docs/release/`; these notes were generated deterministically from git history.",
    ]
    validation_lines = [
        f"- `python scripts/check_release_metadata.py --tag {tag}`",
        "- `python -m unittest tests.test_plugin_manifest_contract tests.test_marketplace_manifest_contract -v`",
        "- `claude plugin validate .` if the Claude Code CLI is available; otherwise rerun the manifest contract tests above.",
        "- `python -m unittest discover -s tests -p \"test_*.py\" -v`",
    ]
    sections = [
        f"# Release {tag}",
        "",
        f"Release date: {release_date}",
        "",
        "## Summary",
        "",
        f"Deterministic fallback release notes for `{tag}` covering {summary_scope}.",
        "",
        "## Highlights",
        "",
        *highlight_lines,
        "",
        "## Compatibility / Upgrade Notes",
        "",
        *upgrade_lines,
        "",
        "## Validation",
        "",
        *validation_lines,
        "",
    ]
    return "\n".join(sections)


def git_stdout(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip()
        raise ReleaseNotesError(
            f"Git command failed ({' '.join(args)}): {stderr}"
        ) from exc
    return completed.stdout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select a curated release document or generate deterministic fallback release notes."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to inspect.",
    )
    parser.add_argument(
        "--tag",
        help="Release tag, for example v2.0.1. Optional if --version is provided.",
    )
    parser.add_argument(
        "--version",
        help="Release version, for example 2.0.1. Optional if --tag is provided.",
    )
    parser.add_argument(
        "--ref",
        default="HEAD",
        help="Git ref to use when generating fallback notes. Defaults to HEAD.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output file for the generated markdown body.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.tag and not args.version:
        parser.error("one of --tag or --version is required")

    version = args.version or args.tag
    try:
        result = build_release_notes(
            args.repo_root,
            version=version,
            tag=args.tag,
            ref=args.ref,
        )
    except ReleaseNotesError as exc:
        print(f"release notes build failed: {exc}", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.body, encoding="utf-8")
        print(f"wrote release notes to {args.output}")
    else:
        sys.stdout.write(result.body)
        if not result.body.endswith("\n"):
            sys.stdout.write("\n")

    if result.source_path is not None:
        print(f"source=document:{result.source_path}", file=sys.stderr)
    else:
        print(
            f"source=generated previous_tag={result.previous_tag or 'none'} commits={result.commit_count}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
