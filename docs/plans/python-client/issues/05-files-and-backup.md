# 05 Files and backup

Status: ready-for-agent
Blocked by: 02

Spec: [../spec.md](../spec.md). Source: the files methods of both `devbench.py` files, both `backup.py` files.

## What

- `devbench.files`: `list_files`, `read_bytes` (None when there is no file), `read_text` (UTF-8 with BOM, else
  cp1252), `write_bytes`, `delete_file`, all through the `files` tool.
- `Backup(bench, globs, folder)`: `pending()`, `take()` (manifest written whole: `.partial` then replace), `restore()`
  (write what differs, delete what the globs list now that the manifest lacks, case-insensitive, then remove the
  manifest; returns written and deleted).

## Acceptance

Unit tests against a fake `files` tool with an in-memory file set: take then restore round-trips, a file the run
created is deleted, a changed file is written back, an unchanged one is not written, a partial manifest is not
pending.
