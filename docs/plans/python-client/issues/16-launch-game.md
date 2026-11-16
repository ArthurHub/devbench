# 16 Launch and restart the game

Status: resolved
Blocked by: 10, 15

Spec: [../spec.md](../spec.md).

## What

The client does not know about MO2, Steam or SteamVR; it runs a command the user gives it.

- `devbench.process.launch(command, game, vr, cwd=None, timeout=300, port=None) -> Devbench`:
  - `command` is a string (on Windows handed to `CreateProcess` as is, no shell) or a list. It starts detached (own
    process group, no console, std streams to `DEVNULL`), so stopping the caller leaves the game running.
  - A game port that already accepts a connection (`port`, else `find_port`) raises `DevbenchError` and nothing is
    launched: a slow live game must not get a second instance on the next port.
  - Then it waits, polling once a second, for devbench to answer and for the game to be ready. The port is read again
    from `runtime.json` on each poll (the new game rewrites it, and may bind past the default) unless `port` pins it;
    an answer counts only when health's `game` and `vr` match. A `runtime.json` left by an earlier run is no proof:
    liveness is `/api/health`.
  - A fresh game can take seconds to answer a new connection (`docs/plans/server-latency/issues/01`), so the wait keeps
    one kept-alive connection and gives a call up to 30 s.
  - Ready on Fallout 4: `MainMenu` open, or a game loaded (HUD up, no `LoadingMenu`) for a setup that loads a save at
    start; the check lives in `games/fallout4.py`. On Skyrim, devbench answering is enough.
  - A launcher that hands off and exits (`ModOrganizer.exe run ...` with MO2 open) is no error; a timeout says what it
    last saw (no port, another game, no main menu with the open menus) and the launcher's exit code.
  - Returns a client of the game, checked to be `game` / `vr`.
- `restart(bench, command, game, vr, cwd=None, timeout=300, kill_after=None)`: `quit_game` then `launch`; returns the
  new `Devbench`. game / vr are explicit so a crashed game, whose health says nothing, restarts too.
- The command comes from `--devbench-launch` or `DEVBENCH_LAUNCH` (the option wins), never from the mod's checked-in
  conftest: it is the user's setup (instance, profile, paths), not the mod's. For FO4VR through a portable MO2:

  ```
  "<MO2 folder>\ModOrganizer.exe" -p <profile> run -e "<executable title>"
  ```

  `-e` makes `run` take one of MO2's executables by its title; without it MO2 looks for a file of that name.

- Plugin:
  - `_connect`: when nothing answers on the port and a launch command is set, launch instead of exiting; this covers
    `--e2e-restore` too. `--devbench-port` pins the port. The terminal shows a line before the launch and one after it
    with how long the game took to be up; the report notes that time, not the command.
  - `--devbench-quit` quits the game in the `bench` fixture's teardown (after the `game` fixture put the backup and
    handedness back, also after a setup failure exited the run), whether or not the run launched it, with
    `kill_after=60`; the report notes it.

## Acceptance

Unit tests with a fake launcher that starts the fake server after a delay (also one that hands off and exits), and one
that never does (timeout message); a game already answering refuses the launch. pytester tests for the plugin's launch
and quit. Live: an unattended run of the flashlight suite from a closed game through MO2 to a finished report in FO4VR;
the client README and `docs/FALLOUT4.md` record it.

Done 2026-11-16 on FO4VR 1.2.72 through a portable MO2 2.5.2: the flashlight suite ran from a closed game to a report
twice, once with MO2 open (the new `ModOrganizer.exe` handed off and exited) and once with MO2 closed (it stayed up
while the game ran and exited with it). The main menu was up 18-19 s after the launch, and `--devbench-quit` quit the
game both times.
