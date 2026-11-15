# 18 Handedness

Status: ready-for-agent
Blocked by: none

Spec: [../spec.md](../spec.md). Source: the flashlight suite's `set_left_handed`, `physical_hand` and its
`--left-handed` option.

## Why

A suite that runs left-handed sets `bLeftHandedMode:VR` through a console `setini` and then waits on its own mod to
follow. Nothing confirms the game took the setting: the flashlight's left-handed run of 2026-11-15 12:41 errored all 58
tests with "the mod reading bLeftHandedMode:VR 1 did not hold within 5 s", and the run could not tell whether the game or
the mod did not follow. Each suite also maps its logical hands to the controllers by hand.

A live probe on 2026-11-15 (FO4VR, ready-pose hold) showed the game follows a runtime change: `PrimaryWandNode` and
`SecondaryWandNode` swap controllers both ways a few frames after the setting changes, not on the same frame. With the
headset idle the physical controllers are untracked and both wands sit at the room origin, so a swap can only be seen
under a held pose.

## What

### Server (Fallout 4 VR)

- **`input action=handedness`**: without `leftHanded` it reads, answering `{leftHanded}`. With `leftHanded: bool` it
  sets it through the console's `setini` on the main thread and answers `{leftHanded, was, changed, elapsedMs}`.
  Writing the setting object alone changes the value but the wands never swap (verified live 2026-11-15): `setini`
  does more than the write. Setting the value it already has answers at once with `changed: false`: no
  hold, no check.
- **The check**: a set confirms the wands swapped, reading the wand slots directly (not `ReachHandWorld`/`WandNode`,
  which map through the setting and would make the check circular). Before the set it records where each wand slot
  sits; after it, it polls each frame until `primaryWandNode` sits where `secondaryWandNode` was and the other way round,
  within 2 units, for about 2 s.
- **Whose hold**: it takes `owner` as `press` does. A running pose hold of that owner: the check runs under it. No
  sequence running: it takes a short ready-pose hold as `devbench:handedness`, checks and hands the devices back.
  Another owner's sequence, or a frame `sequence` playing (moving controllers): 409. Held hands closer than about 10
  units (both placed in one spot): 409 "hands too close to tell", before setting. `vrTrackedSet` not ready: 503 before
  anything is set.
- **A set that does not take**: after the timeout it puts the old value back and fails 504 with what it saw (the
  setting's value, the wand positions, the controller expected).
- **`capabilities`** reports `leftHanded`, read live.
- **Logical hands**: `primary` and `offhand` work beside `left`/`right` in `press.hand`, the `pose` `hands` keys and
  `head.lookAt`, resolved live from the handedness. Answers stay keyed by physical `left`/`right` and carry
  `leftHanded`. Two names for one controller in one request (`left` + `primary` while left-handed) answer 400.
- Skyrim answers 501 for the action and the logical names until it is done there.

### Client

- `devbench.vr.left_handed(bench) -> bool` and `set_left_handed(bench, value) -> bool` (the value before).
- `Hands.press`/`place` accept `primary`/`offhand` beside `left`/`right` and validate against the four names; the
  server resolves them, the client has no resolver.

### Plugin

- `Config(handedness=None | "left" | "right")`: None leaves the player's setting alone. A built-in `--left-handed`
  option overrides it (there is no `--right-handed`). `Config` rejects another value, and a handedness with `vr=False`.
- The set happens in `game` before it yields, so a mod's own `game` wrapper can then wait for its mod to follow. A set
  that fails is a setup failure (exit code 2 with the evidence).
- The player's value is written to `.backup/handedness.json` (`{"leftHanded": <value>}`) before the set and put back at
  the end of the run, before the files, also when the session fails; the file is deleted once that succeeds. A run that
  finds one at start puts that value back before setting its own, as for files. `--e2e-restore` that cannot reach the
  game still puts the files back, keeps the handedness file and says so.
- The report notes "Ran left-handed." / "Ran right-handed." whenever the plugin set it; a session fixture
  `left_handed` answers the run's value.

## Acceptance

Unit tests: the client's getter, setter and `Hands` names against the fake server; the plugin sets and restores the
handedness, also when the session fails, and the `.backup/handedness.json` cases (left by a crash and restored at
start, kept by an `--e2e-restore` without a game). Bridge tool fallback synced. Live check in FO4VR: set left-handed, a
`press` on `offhand` lands on the right controller, a set under a caller's hold, set back; `docs/FALLOUT4.md` records
it.
