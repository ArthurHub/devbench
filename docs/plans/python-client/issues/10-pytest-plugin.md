# 10 pytest plugin

Status: resolved
Blocked by: 03, 05, 06, 07, 08

Spec: [../spec.md](../spec.md). Source: both conftests.

## What

`devbench.testing`, a package: `__init__` re-exports `Config`, the hooks and the fixtures (`pytest_plugins`
registers that module itself) from private `_config`, `_plugin`, `_record`; ticket 11 adds `report` beside them.

- `Config`, a frozen dataclass: `game`, `vr`, `tool=None`, `actions=[]`, `version=None` (a string or a callable
  called once at the check; None skips it), `backup=[]` ((root, glob) pairs; empty: no backup), `log=None`,
  `areas={}`, `title=None`, `cell="QASmoke"`. `tool=None` means no mod check and unprefixed events.
- At `pytest_configure` the plugin finds the one registered module that defines `DEVBENCH`; none or several is a
  `pytest.UsageError` naming them. pytest honors `pytest_plugins` only in the rootdir conftest, so both lines go there.
- Options `--devbench-port` (else `find_port(game, vr)`), `--e2e-restore`: at session start, connect, `require` the
  game and VR (a restore through the wrong game writes its files), restore and exit; nothing pending exits 0.
- `bench` (session, lazy: `--collect-only` never touches the game): connect, `require` game and VR.
- `game` (session, yields the `Devbench`): restore a leftover backup, `enter_game(cell)` (a settle that never went
  quiet is a note), then `require_tools([tool])`, `require_actions`, `require_version`; take the backup into
  `<dir of the DEVBENCH conftest>/.backup/`, set the log mark. At the end restore the backup, also when the session
  fails; a failed restore keeps the manifest and errors with the `--e2e-restore` hint.
- Every setup failure is `pytest.exit(message, returncode=2)`.
- `mod` (session): `ModTool(game, tool)`. `events` (per test, on `game`, the mod's prefix). `log_mark` (session,
  `LogMark(bench, log)`, no automatic error check). `mod` without `tool` and `log_mark` without `log` are usage errors.
- `report`: the run's record: `note(text)`, `dialogs` (the dialogs the run closed), results (nodeid, area, outcome,
  phase, duration, failure text) from `pytest_runtest_logreport`. Ticket 11 renders it.
- Tests sorted by `areas` (keys are test-file basenames), stable; unlisted files last in collected order.
- A mod's own session setup overrides `game` with a fixture of that name that requests the plugin's and wraps it; no
  hook. Its setup runs after the backup and the log mark, its teardown before the restore.
- `clients/python/README.md` documents the plugin. No live run here: ticket 13 is the live acceptance.

## Acceptance

Tests with pytester (in-process) and the fake server scripted as a game already in the cell: a run with a Config
connects, backs up and restores; a missing action exits with its message; `--e2e-restore` restores and runs no test;
areas order the tests.
