# 09 VR hands

Status: resolved
Blocked by: 02

Spec: [../spec.md](../spec.md). Source: `Controllers` in the flashlight suite's `controllers.py`, without the
gesture-zone aiming and the report coupling (both stay in the mod).

## What

`devbench.vr.Hands(bench, owner)`: `ready()` (the vrTrackedSet capability), `start()` (ready pose), `rest()`,
`place(hand, world, **placement)` returning devbench's answer (corrections), `head(preset_or_pose)`,
`press(hand, buttons, duration_ms)`, `tap`, `long_press`, `stop()`. It keeps the control token, and is a context
manager that always stops, so a failure never leaves the headset held. Hands are physical (`left`/`right`); mapping a
mod's logical hand stays in the mod.

## Acceptance

Unit tests: the token is kept and passed to stop, stop runs on an exception inside the `with`. Live check in FO4VR:
start, place, press, stop hands the devices back.

## Verified

FO4VR, 2026-11-15, in QASmoke: `ready()` read True from the real capabilities answer. `with Hands(...)` started the
hold (status `active`, a token kept); `place("left", ...)` 10 units above the wand landed 0.006 units off with 0
corrections; `head("down")`, `tap("left")`, `long_press("right", ["grip"])` and `rest()` were accepted over the hold.
Leaving the `with` stopped it (status inactive, token cleared), and so did a `RuntimeError` raised inside one. A press
without a hold raised `DevbenchError` 409. Whether the presses reached the game's input handling was not observed.
