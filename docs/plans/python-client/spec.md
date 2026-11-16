# Spec: devbench Python client and E2E plugin

Status: needs-triage

## Problem

Mods test themselves in the running game through devbench's REST port, and each mod writes the same Python to do it.
Immersive Flashlight (`F4VR-ImmersiveFlashlight/tests/e2e`) and Mods Config (`F4VR-Mods-Config/tests/e2e`) each carry a
`devbench.py`, `backup.py`, `report.py` and a conftest whose start-game, settle and close-dialog code is the same, kept
in step by hand. devbench's own Skyrim suite (`tests/http/conftest.py`) is a third take on discovery and bootstrap.

## Goal

One Python package in this repo, in two layers:

- **Client library**: helpful abstractions over devbench's REST API, usable from a script, a REPL or an agent. It never
  imports pytest.
- **E2E layer**: a thin pytest plugin on the client: fixtures, run setup and teardown, the version check, the HTML
  report. A mod turns it on with one line.

A mod keeps its own actions (`flashlight.py`, `menu.py`), loadout, baseline settings and tests.

## Decisions

- **Lives in** `clients/python/`, `src/` layout. Licensed MIT (own `LICENSE` in that folder), like `include/DevBenchAPI.h`.
- **Distribution** `devbench-client`, import package `devbench`; the pytest plugin is `devbench.testing`.
- **Published by git tag**, no PyPI. A mod's requirements line picks the remote and the tag:
  `devbench-client @ git+https://github.com/ArthurHub/devbench@fo4-v1.0.0#subdirectory=clients/python`.
  Local work on both: `pip install -e <devbench>/clients/python`.
- **Version comes from the git tag** (setuptools-scm with `root = "../.."`, describing `--match fo4-v*`), so the
  package and the DLL's displayed version share a number and nothing is bumped by hand. The fork's release scheme is
  ticket 17.
- **Dependencies**: `requests` is not needed; the client keeps the `http.client` kept-alive connection the suites use
  (a connection per call exhausts local ports when a test polls). `pytest` is a plain dependency (the plugin needs it;
  the client does not import it). Image comparison deps, if they ever move in, go behind a `[visual]` extra.
- **Plugin is opt-in**: `pytest_plugins = ["devbench.testing"]` in the mod's conftest. No `pytest11` entry point, so it
  never loads into an unrelated pytest run.
- **Mod config** is a module-level object the mod's conftest defines (read at `pytest_configure`, so `--e2e-restore`
  can use it before fixtures exist):
  ```python
  pytest_plugins = ["devbench.testing"]
  DEVBENCH = devbench.testing.Config(
      game="fallout4", vr=True,
      tool="immersiveflashlightvr", actions=["gesture", "zones", "light"],
      version=lambda: ...,                     # the checkout's version; compared with the mod tool's health
      backup=[("mygames", "Mods_Config/ImmersiveFlashlightVR/*")],
      log="ImmersiveFlashlightVR.log",
      areas={"test_light.py": "Light action", ...},
      title="Immersive Flashlight VR",
  )
  ```
- **Missing tool or action stops the run** (`pytest.exit`) for a mod's suite. Skipping per test, as devbench's own
  suite does, is not in this spec.
- **Game setup is per game**: `devbench.games.fallout4`. The client core stays game-neutral.

## Client API (summary; tickets have the detail)

| Module                                | Holds                                                                                                                                                                          |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `devbench.client`                     | `find_port(game, vr)`, `Devbench(port)`, `tool()`, `health()`, `ModTool` (a mod's own tool by action), `DevbenchError`                                                         |
| `devbench.checks`                     | `require(game, vr)`, `require_tools`, `require_actions`; raise `RequirementError`                                                                                              |
| `devbench.waits`                      | `wait_until(check, timeout, interval, what)`                                                                                                                                   |
| `devbench.events`                     | `Events` (from now on; `all(topic)`, `wait(topic, where)`)                                                                                                                     |
| `devbench.console` / `devbench.menus` | `console`, `console_number`; `open_menus`, `close_dialogs`, `close_menus`                                                                                                      |
| `devbench.files`                      | read/write bytes and text, list, delete; `Backup(globs, folder)` with a crash-safe manifest                                                                                    |
| `devbench.log`                        | a line mark, the lines since it, errors since it                                                                                                                               |
| `devbench.vr`                         | `Hands`: a held pose as an owner, place a hand at a world point, press/tap/long press, release                                                                                 |
| `devbench.games.fallout4`             | `enter_game(cell="QASmoke")`, `settle()`, `in_cell()`; items, weapon and power armor over the console and the `player` tool (`equip`, `draw_weapon`, `leave_power_armor`, ...) |
| `devbench.process`                    | `quit_game` (`qqq`, wait for the process to exit), `wait_gone`, `launch(command)` (run the user's command, wait for devbench and the main menu), `restart`                     |

Launching runs a command the user gives (`DEVBENCH_LAUNCH` or `--devbench-launch`); the client knows nothing about
MO2, Steam or SteamVR, and the command never lives in a mod's checked-in conftest.

Python is formatted and linted with ruff through pre-commit, limited to `clients/python/`, set up before any client
code lands.

## Out of scope

- Moving devbench's own Skyrim suite (`tests/http`) onto the client. A follow-up once the Fallout side is proven.
- Skyrim game setup (`devbench.games.skyrim`).
- PyPI.

## Testing

Unit tests in `clients/python/tests/` run against a fake devbench (a local `http.server` thread that answers
`/api/tool/<name>`, `/api/events`, `/api/health` from scripted responses). No game. CI runs them. The acceptance test is
the Immersive Flashlight suite running green in game on the client, then Mods Config's.

## Done when

- The package installs from a git tag with one requirements line, and from a local path in editable mode.
- Both mod suites run on it in game with their own `devbench.py`, `backup.py`, `report.py` and the shared conftest code
  deleted.
- `clients/python/README.md` documents install, the client API and the plugin config.
