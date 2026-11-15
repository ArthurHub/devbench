# 10 pytest plugin

Status: ready-for-agent
Blocked by: 03, 05, 06, 07, 08

Spec: [../spec.md](../spec.md). Source: both conftests.

## What

`devbench.testing`: `Config` (the spec's fields), read from the conftest's `DEVBENCH` at `pytest_configure`.

- Options `--devbench-port`, `--e2e-restore` (restore a pending backup and exit).
- `bench` (session): connect, `require` game and VR, exit with the message on failure.
- `game` (session): restore a leftover backup, enter the game, settle, check the mod's tool, actions and version,
  take the backup, set the log mark; at the end restore the backup, also when the session fails.
- `events` (per test, the mod's prefix), `log_mark` (session), `report` (the run's report object, ticket 11).
- Tests sorted by `areas` order.

## Acceptance

Tests with pytester and the fake server: a run with a Config connects, backs up and restores; a missing action exits
with its message; `--e2e-restore` restores and runs no test; areas order the tests.
