# Bilingual Release Notes Template

Use this template when creating the curated release doc consumed by `scripts/build_release_notes.py`.

Rules:

- Put the main selected file at `docs/release/<date>-vX.Y.Z.md`.
- Keep English first.
- Add `## 中文说明` in the same file for normal releases.
- Keep `Validation` English-only unless you have a strong reason to translate operator commands.
- If the combined body becomes too long, keep a short Chinese summary in the main file and link to a detailed Chinese companion doc under `docs/release/zh-CN/<date>-vX.Y.Z.md`.
- Do not create a second version-matching top-level file in `docs/release/`, or release-doc selection will become ambiguous.

```md
# Release vX.Y.Z

Release date: YYYY-MM-DD

## Summary

One short English paragraph explaining what changed and why this release matters.

## Highlights

- English highlight 1.
- English highlight 2.
- English highlight 3.

## Compatibility / Upgrade Notes

- English compatibility note 1.
- English compatibility note 2.

## 中文说明

### 摘要

一小段中文摘要，说明这次发布解决了什么问题，以及为什么值得关注。

### 重点变更

- 中文重点 1。
- 中文重点 2。
- 中文重点 3。

### 升级提示

- 中文兼容性或升级提示 1。
- 中文兼容性或升级提示 2。

## Validation

- `python scripts/check_release_metadata.py --tag vX.Y.Z`
- `python -m unittest discover -s tests -p "test_*.py" -v`
```

Long-release variant:

- Keep the same top-level `docs/release/<date>-vX.Y.Z.md` file.
- Replace the full Chinese section with `## 中文摘要`.
- Link to `docs/release/zh-CN/<date>-vX.Y.Z.md` for the detailed Chinese notes.
