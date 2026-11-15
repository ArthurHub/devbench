# 19 Pose targets

Status: ready-for-agent
Blocked by: none

Spec: [../spec.md](../spec.md). Source: the flashlight suite's `Controllers.place_in_zone` and `_aim`.

## Why

The flashlight suite places a hand at an offset from a zone's center along the head's axes: it reads `hmdNode`'s
rotation itself, between turning the head and placing the hand, and does the math. It also flips a recorded controller
yaw for the right hand, because the yaw is given as for the left one.

## What

- **Head-relative target**: a hand target in `pose` can be a world point plus an offset (right, forward, up) in the
  HMD's frame, read on the main thread with the placement, so it is the head as posed.
- **Yaw toward the body**: a controller yaw that turns toward the body for either controller, so one recorded pose
  works for the left and the right hand (and so for either handedness).
- **Client**: `Hands.place` takes both.

## Acceptance

Unit tests for the target math in the pure-logic part. Bridge tool fallback synced. Live check in FO4VR: the same
offset and inward yaw place each hand mirrored around the head; `docs/FALLOUT4.md` records it.
