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

## What

- **Server**: the VR seam reads and sets the game's handedness. `input action=handedness` reads it, or sets it and
  waits until the wand nodes have swapped, answering the value before and after (a set that does not take fails with
  what it saw). `capabilities` reports `leftHanded`. `press` and `pose` take `primary` and `offhand` beside
  `left`/`right`, resolved live from the handedness. Fallout 4 VR only; Skyrim answers 501 for the action and the
  logical names until it is done there.
- **Client**: `devbench.vr` reads and sets the handedness (the setter returns the value before); `Hands` passes
  `primary`/`offhand` through and validates them.
- **Plugin**: a built-in `--left-handed` option and `Config(handedness=...)` set it at session start and put the
  player's value back at the end, before the backup restore; the report notes the run's handedness; a session fixture
  answers it.

## Acceptance

Unit tests: the client's setter and `Hands` against the fake server; the plugin sets and restores the handedness, also
when the session fails. Bridge tool fallback synced. Live check in FO4VR: set left-handed, a `press` on `offhand` lands
on the right controller, set back; `docs/FALLOUT4.md` records it.
