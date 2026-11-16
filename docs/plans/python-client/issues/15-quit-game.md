# 15 Quit the game

Status: resolved
Blocked by: 04

Spec: [../spec.md](../spec.md).

## What

devbench's core `quit` tool (both games, through the `host::RequestQuit` seam): sets `Main::quitGame` on the main
thread, the flag the console's `qqq` sets, and answers `{ pid, quitting, killAfterMs }` before the game goes down. On
Fallout the flag's offset is CommonLibF4's flat layout, checked by content first. `killAfterMs` > 0 arms a watchdog
thread that terminates the process if it still runs by then: a shutdown that hangs has usually stopped the listener, so
no later call could end it. Default 0, never kills.

`devbench.process.quit_game(bench, timeout=60, kill_after=None)`: calls `quit` when devbench lists it, else sends `qqq`
through the `console` tool (devbench queues it, see the queued-command list in `src/core/ConsoleCaptureLogic.cpp`).
Then waits until the game's process (the pid from `quit`'s answer or from `/api/health`) has exited, and closes
`bench`. A game that does not answer returns at once; a connection dropped on the call counts as the game going. A
game still there at the timeout raises `DevbenchError` with the pid, whether it runs, and what the port last said.
Nothing is killed unless `kill_after` armed the watchdog, and no dialog is closed first.

`wait_gone(port, pid=None, timeout=60)` for a caller that quit some other way: waits on the process when the pid is
known (read from health when omitted and the port answers), else for the port to stop answering. The process is the
authority, not the port: a game can stop answering while still shutting down, and a `restart` must not launch beside it.

## Acceptance

Unit tests: the fake server stops after `qqq` and the call returns; a server that keeps answering times out; the
`quit` tool is used when listed and its pid waited on. Live check in FO4VR from the main menu and from in game;
`docs/FALLOUT4.md` records it. Skyrim: builds; no live run here.
