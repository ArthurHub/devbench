# 04 Console and menus

Status: ready-for-agent
Blocked by: 02

Spec: [../spec.md](../spec.md). Source: `console`, `console_number`, `open_menus` (flashlight `devbench.py`),
`close_dialogs` (both conftests), `close_game_menus` (flashlight `flashlight.py`), the console-buffer priming in
Mods Config's `_start_game`.

## What

- `devbench.console`: `console(bench, command)` (not compiled raises), `console_number(bench, command)` (the number
  after `>>`), `prime_console(bench)` (open and close the Console menu so its buffer keeps what commands print).
- `devbench.menus`: `open_menus(bench)`, `close_dialogs(bench, limit=20)` answering each message box with its first
  button and returning what each said, `close_menus(bench, names)` ignoring a refusal.

Free functions or methods on `Devbench`: pick one style here and keep it for the later tickets.

## Acceptance

Unit tests: a number parsed from console output, no number raises, `close_dialogs` answers until none is open and
returns the texts, a box whose describe fails is still answered.
