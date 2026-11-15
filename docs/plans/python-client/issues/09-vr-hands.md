# 09 VR hands

Status: ready-for-agent
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
