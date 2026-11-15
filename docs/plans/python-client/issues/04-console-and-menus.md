# 04 Console and menus

Status: resolved
Blocked by: 02

Spec: [../spec.md](../spec.md). Source: `console`, `console_number`, `open_menus` (flashlight `devbench.py`),
`close_dialogs` (both conftests), `close_game_menus` (flashlight `flashlight.py`).

## What

- `devbench.console`: `console(bench, command)` (not compiled raises), `console_number(bench, command)` (the number
  after `>>`; none, or output not captured, raises `DevbenchError`). No priming: devbench's `console` tool makes the
  Console menu itself before its first capture, so Mods Config's open-and-close in `_start_game` is not ported.
- `devbench.menus`: `open_menus(bench)`, `close_dialogs(bench, limit=20)` answering each message box with its first
  button and returning what each said, `close_menus(bench, names)` ignoring a refusal.

Free functions taking `bench` first, the style the later tickets keep; a class only where there is state (`Events`,
`Hands`). `Devbench` stays the transport.

## Acceptance

Unit tests: a number parsed from console output, no number raises, `close_dialogs` answers until none is open and
returns the texts, a box whose describe fails is still answered.
