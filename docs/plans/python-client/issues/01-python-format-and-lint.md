# 01 Python formatter and linter

Status: resolved
Blocked by: none

Spec: [../spec.md](../spec.md). Comes first so every later ticket lands formatted and lint-clean.

## What

- Add ruff to `.pre-commit-config.yaml` (`astral-sh/ruff-pre-commit`, hooks `ruff-check --fix` and `ruff-format`),
  limited to `^clients/python/`. The Skyrim suite in `tests/http/` stays out: pre-commit.ci runs on all files, and
  reformatting upstream's Python is not this work.
- ruff config in `clients/python/pyproject.toml` (`[tool.ruff]`): line length 120 (the mod suites' width), target the
  lowest Python the package supports, lint rules `E`, `F`, `W`, `I` (imports), `B` (bugbear), `UP` (pyupgrade).
  The pyproject here holds only the ruff config; ticket 02 fills in the package.
- Runs on pre-commit.ci with no extra setup (ruff ships as a binary wheel, unlike the eslint hook it skips).

## Acceptance

`pre-commit run --files <a .py file under clients/python/>` formats and lints it; a `.py` file under `tests/http/` is
not touched.
