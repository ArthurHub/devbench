# 15 Quit the game

Status: ready-for-agent
Blocked by: 04

Spec: [../spec.md](../spec.md).

## What

`devbench.process.quit_game(bench, timeout=60)`: sends `qqq` through the `console` tool (devbench queues it, see the
queued-command list in `src/core/ConsoleCaptureLogic.cpp`), then waits until `/api/health` stops answering on the
port. A game that still answers at the timeout raises with what it last reported. Also `wait_gone(port, timeout)` for
a caller that quit some other way.

## Acceptance

Unit tests: the fake server stops after `qqq` and the call returns; a server that keeps answering times out. Live check
in FO4VR from the main menu and from in game; `docs/FALLOUT4.md` records it.
