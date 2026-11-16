# 22 Fallout 4 player helpers

Status: resolved
Blocked by: none

Spec: [../spec.md](../spec.md). Source: the flashlight suite's `Loadout`, without the mod's headgear read.

## Why

The flashlight suite wraps the console and devbench's `player` tool for the loadout a test needs, and checks each
`player` answer's outcome by hand. FRIK's suite and others will need the same.

## What

In `devbench.games.fallout4`:

- Items through the console: the player's count of a form, equip (adding one first when there is none), unequip.
- Weapon: draw and sheathe through the `player` tool; `switched` and `already` return the answer, anything else raises
  with the outcome, the weapon state and the note.
- Power armor: find the nearest frame, enter and exit at once, step in and out; same outcome rule. Leaving power armor
  falls back to stepping out when the scripted exit is refused (a mod such as KabutoVR blocks it).

## Acceptance

Unit tests against the fake server: each outcome rule, the equip that adds first, the exit fallback. Live check in
FO4VR in QASmoke: equip, draw, sheathe, in and out of a frame both ways.
