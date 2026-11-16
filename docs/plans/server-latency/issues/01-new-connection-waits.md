# 01 A new connection waits seconds for its first answer

Status: needs-triage

## What was seen

FO4VR 1.2.72, 2026-11-16, three launches while live-checking the `quit` tool (python-client issue 15):

- The first request on a new connection (`GET /api/health` from `devbench.Devbench`) took 4–20 s: 19.7 s, 15.8 s,
  4.5 s in game; over 2 s at the main menu on a fresh launch; 18.3 s in game on the next launch.
- Later requests on that same kept-alive connection (`memory` reads, `/api/tools`, `menu`) answered at once.
- `Get-NetTCPConnection -LocalPort 8931` showed about 40 `Established` connections owned by the game, plus many in
  `TimeWait` and two in `CloseWait`.

The handler is not the cost: `/api/health` (`src/core/RestAdapter.cpp`) answers on the listener thread from atomics and
a mutex, without the main thread.

## Hypothesis (unverified)

New connections queue for a free httplib worker while kept-alive or streaming connections (the bridge, MCP sessions,
earlier clients that never closed) hold all of them. That fits "the first request is slow, the rest are fast".

## To find out

- Worker pool size and keep-alive settings of the server (cpp-mcp / httplib in `src/core/Server.cpp`), and whether an
  MCP or SSE stream holds a worker for its whole life.
- Who owns the ~40 connections (remote ports → processes), and whether they grow over a session.
- Time the first request on a new connection against the number of open ones.

## Why it matters

A liveness check with a short timeout reads a live game as silent: `devbench.process`'s 2 s probe missed the pid at
the main menu and in game. `quit_game` still worked (the `quit` tool's answer carries the pid), but a `qqq` fallback
or `wait_gone` without a pid would wait on the port instead of the process. `launch` (python-client issue 16) works
around it: it counts a port that accepts a connection as held, and while waiting gives each call on its one kept-alive
connection up to 30 s.
