# 16 Launch and restart the game

Status: ready-for-agent
Blocked by: 10, 15

Spec: [../spec.md](../spec.md).

## What

The client does not know about MO2, Steam or SteamVR; it runs a command the user gives it.

- `devbench.process.launch(command, game, vr, cwd=None, timeout=300)`: starts the command detached, then waits for
  devbench to answer on the game's port and for the main menu to be up. A launcher that hands off and exits
  (`ModOrganizer.exe run ...` does) is not an error; a timeout says what it last saw (no port, port but no main menu).
  A `runtime.json` left by an earlier run is not proof: liveness is `/api/health`.
- `restart(bench, command, ...)`: `quit_game` then `launch`; returns a new `Devbench`.
- The command comes from `DEVBENCH_LAUNCH` (env) or `--devbench-launch`, never from the mod's checked-in conftest:
  it is the user's setup (instance, profile, paths), not the mod's.
- Plugin: when no game answers and a launch command is set, launch it instead of exiting; `--devbench-quit` quits the
  game when the session ends.

## Acceptance

Unit tests with a fake command that starts the fake server after a delay, and one that never does (timeout message).
Live: an unattended run from a closed game through MO2 to a finished report in FO4VR.
