# 11 HTML report

Status: resolved
Blocked by: 10

Spec: [../spec.md](../spec.md). Source: both `report.py` files.

## What

`devbench.testing.report` (public: `render(record) -> str`, `write(record, folder=None) -> Path`) renders the run's
`Record` without a pytest session. The plugin writes it in `pytest_terminal_summary` and prints `Report: file:///…`;
nothing on `--collect-only`, `--e2e-restore` or a run without results.

- **Where**: `<root>/<YYYYmmdd-HHMMSS>/index.html`. `<root>` is `build/e2e` under the first folder up from the
  `DEVBENCH` conftest with a `.git` (else that folder), or `Config.report_dir` (relative: to that folder).
- **Page order**: header (title = `Config.title or tool or game`, date, duration, test count), totals (passed / failed
  / error / skipped), notes, failures, areas (`Config.areas` order, then unlisted files named by file), mod sections,
  dialogs closed, gallery. Light and dark styling kept (`prefers-color-scheme`).
- **On a failure** (first failed phase of a test that uses `game`, while the game is up; a `pytest_runtest_makereport`
  wrapper, so before teardown): the last 100 lines of `Config.log` since a per-test mark (autouse fixture, one
  `log tail` per test), collapsed; and a picture of render target `Config.picture` (None: none): `rendertarget dump`
  at `maxDimension` 2048, read through `files` (root `data`), the game's copy deleted, saved as
  `pictures/NNN-<test>.png` (written with `zlib`, no Pillow; about 1.3 MB); in VR cropped to the left eye (the target
  holds both side by side), 1024x1088 on FO4VR.
  The first picture that fails says why in its row and in one note, and pictures stay off for the run. A setup
  failure with the crash (file, line, message) of one already captured takes nothing: a failed session fixture
  fails every later test's setup with the same error, and only its first test gets the picture and log tail.
- **Section API** on the `report` fixture: `section(title, *, intro, columns, rows, html)`. The same title appends; a
  section is a table (escaped cells) or raw HTML; other columns, a row of another length or the other shape raise
  `ValueError`; the first intro given stays. Sections render after the areas, in first-added order.
- **Mod pictures**: `picture(nodeid, label=None, suffix=".png") -> Path` reserves a file the mod writes; shown in the
  test's row (a picture column only where some test has one) and in the gallery, when the file exists at write time.
  Failure pictures show only in their failure row.
- `folder` (created on first use) lets a mod write its own files beside the page (`perf.json`).
- Moved to the mods: the sweep is its own section (no area-table replacement), known issues go in its intro, no tile
  API.
- The `report` fixture is declared `name="report"` on `report_fixture`, so the package's `report` attribute stays the
  module.

## Acceptance

pytester run against the fake (scripted `rendertarget`, `files`, `log`): the page has each area in order, a failure
section with its picture and log tail, a mod section and the gallery; a failed picture is noted once and not retried.
Unit tests of `render()` on hand-built records: escaping, section shapes, picture columns, light and dark styling.

Live check (FO4VR, devbench 1.32.0, 2026-11-15), a throwaway two-test suite from the main menu: a new game in QASmoke,
the page in area order with the failure, the mod section and the dialogs closed; the failure's picture copied beside
the page and the game's capture deleted (the dump's `file` is relative, `Data\F4SE\…`); a 9-line log tail of
`devbench.log`; an undecodable target (12) noted once; the left-eye crop at 2048 (0.3 s for the run). Render target 6
(R8G8B8A8, 6144x3264, both eyes) is the lit, fogged frame; 29 and 30 hold the same; 25 is albedo, 3 and 4 HDR. Not
checked: which target shows with a menu or the Pip-Boy open. Ticket 13 is the acceptance on a mod's suite.
