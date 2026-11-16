# 20 Failure diagnostics

Status: resolved
Blocked by: none

Spec: [../spec.md](../spec.md). Source: the flashlight suite's `Flashlight.wait`, `blocked_by` and its log-warning
regex; Mods Config's wait for a new state frame.

## Why

The flashlight's run of 2026-11-15 13:57 failed with "inert: a game menu blocks the gestures", and nothing in the
failure said which menu. A `wait_until` timeout says only "did not hold", so each suite wraps it to show the last state
it read.

## What

- **Failure capture**: a failed test's report entry lists the open menus and, when a message box is up, its text. The
  message-box description that `close_dialogs` uses becomes a public helper.
- **`wait_for(read, condition, timeout, what, describe=None)`**: polls `read`, returns the value `condition` accepts,
  and on timeout raises with the last value (through `describe` when given).
- **`LogMark.warnings()`**: the warning lines since the mark, in both log formats, beside `errors()`.

## Acceptance

Unit tests against the fake server: a failure records the menus and a box's text, a menu read that fails leaves a note
instead; `wait_for`'s error carries the last value; `warnings()` matches both formats.
