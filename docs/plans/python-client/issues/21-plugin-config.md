# 21 Plugin config

Status: resolved
Blocked by: none

Spec: [../spec.md](../spec.md). Source: the flashlight suite's `pytest.ini` markers and `pytestmark` lines, its
`_check_frik` and ready wait, and the `PYTEST_CURRENT_TEST` parsing in `controllers.py`.

## Why

An area is named in three places: `Config.areas`, a marker in `pytest.ini`, and a `pytestmark` in its file. A suite
that depends on another mod's devbench tool checks it in its own fixture, and waits for its own mod to be up the same
way. A report section that lists rows per test parses pytest's environment variable for the test name.

## What

- **Areas carry their marker**: an area names its marker; the plugin registers it and marks the file's tests, so
  `-m <area>` works with nothing else declared. The plain title form keeps working.
- **`Config.requires`**: other mods' tools the run needs, each with the actions it calls and a minimum version,
  checked at start like the mod's own (a miss stops the run).
- **`Config.ready`**: a condition on the mod's tool waited on before the first test, with a timeout.
- **Current test in the report**: a section row can be tagged with the running test without the suite reading pytest's
  environment.

## Acceptance

pytester tests against the fake server: `-m <area>` selects that file's tests; a missing required tool, action or a
low version stops the run with what is missing; a ready condition that never holds stops it; a row added in a test
carries that test's name.
