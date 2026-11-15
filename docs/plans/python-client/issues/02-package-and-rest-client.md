# 02 Package skeleton and REST client

Status: resolved
Blocked by: 01

Spec: [../spec.md](../spec.md). Source to extract: `F4VR-ImmersiveFlashlight/tests/e2e/devbench.py`, with
`health()` and `read_text` from `F4VR-Mods-Config/tests/e2e/devbench.py`.

## What

- `clients/python/`: `pyproject.toml` (distribution `devbench-client`, import `devbench`, setuptools-scm with
  `root = "../.."`, deps: pytest), MIT `LICENSE`, `README.md` (install lines), `src/devbench/`.
- `devbench.client`: `DevbenchError`; `Devbench(port)` with the kept-alive `http.client` connection that reopens once
  when the game closed it; `tool(name, **args)` (non-200 or `ok: false` raises); `health()`; `close()`; context manager.
- `find_port(game, vr)`: `%LOCALAPPDATA%/devbench/<id>/runtime.json` (id `se`, `vr`, `fallout4`, `fallout4vr`, as
  `src/core/Server.cpp` writes it), else the game's default port (8920, 8921, 8930, 8931).
- `ModTool(bench, name)`: `call(action, **args)`, `health()`; its event prefix is its name.
- `devbench.waits.wait_until(check, timeout, interval=0.1, what=...)`: returns the true value, raises `TimeoutError`.
- `clients/python/tests/`: the fake devbench server fixture every later ticket's tests use.

## Acceptance

- `pip install -e clients/python` works; `python -c "import devbench"` does not import pytest.
- Unit tests cover: a call, a refusal, the reconnect after the server drops the connection, `find_port` from a
  runtime.json and from the default, `wait_until` success and timeout.
