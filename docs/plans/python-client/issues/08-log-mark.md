# 08 Log mark

Status: ready-for-agent
Blocked by: 02

Spec: [../spec.md](../spec.md). Source: `log_line_count` in the flashlight conftest and its `test_health.py` log
check.

## What

`devbench.log.LogMark(bench, file)`: records the line count now; `lines()` since the mark; `errors(pattern=...)` since
the mark.

## Acceptance

Unit tests against a fake `log` tool; live check that a mark taken before a console command sees the lines after it.
