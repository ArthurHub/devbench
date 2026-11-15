# 08 Log mark

Status: resolved
Blocked by: 02

Spec: [../spec.md](../spec.md). Source: `log_line_count` in the flashlight conftest and its `test_health.py` log
check.

## What

`devbench.log.LogMark(bench, file)`: records the line count now; `lines()` since the mark; `errors(pattern=...)` since
the mark.

## Acceptance

Unit tests against a fake `log` tool; live check that a mark taken before a console command sees the lines after it.

## Verified

FO4VR, 2026-11-15: a mark on `devbench.log` (15 lines) read nothing new right after it; after a console command and a
`files` write and delete in `mygames`, `lines()` returned exactly the two `files:` info lines, `missed` 0, `errors()`
empty. A console command logs nothing at info level, so the `files` calls are what the mark saw. A mark on a missing
log raised `DevbenchError` (404).
