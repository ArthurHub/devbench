# 05 Files and backup

Status: resolved
Blocked by: 02

Spec: [../spec.md](../spec.md). Source: the files methods of both `devbench.py` files, both `backup.py` files.

## What

- `devbench.files`, free functions taking `bench` first, all through the `files` tool: `list_files` (a listing that
  is `incomplete` or `capped` raises, since a backup from it would miss files and its restore delete them),
  `read_bytes` (None when there is no file: a 404 whose error is `files: no file`, as an unknown tool is a 404 too),
  `read_text` (UTF-8 with BOM, else cp1252), `write_bytes`, `write_text` (UTF-8, no BOM), `delete_file`.
- `Backup(bench, globs, folder)`: `pending()`, `take()` (returns the file count; manifest written whole: `.partial`
  then replace; raises while a backup is pending), `restore()` (write what differs, delete what the manifest's globs
  list now that the manifest lacks, case-insensitive, then remove the manifest; returns written and deleted as
  `root/path`; raises when nothing is pending). The manifest format is the mods' own, so a manifest an old mod run
  left is restored. `folder` has no default; the plugin picks it.

## Acceptance

Unit tests against a fake `files` tool with an in-memory file set: take then restore round-trips, a file the run
created is deleted, a changed file is written back, an unchanged one is not written, a partial manifest is not
pending.
