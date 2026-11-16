# 19 Pose targets

Status: resolved
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

## Decisions

- **`headOffset: [outward, forward, up]`** on world targets only (400 on a node target), world units within
  `kOffsetLimit`. Outward is toward the physical hand's own side (after primary / offhand resolve), so one offset
  mirrors around the head. The caller scales it (the suite passes `radius * edge`).
- **Head frame**: `hmdNode`'s world rotation rows (right, forward, up, pitch included), read through a new
  `vrhost::HmdAxes()` seam on the main thread after the head turn, only when a hand carries `headOffset`. Skyrim's
  stub answers 501 like `HmdWorld()`. The offset resolves once, before the hands move; corrections chase that point and
  the answer's `target` is it.
- **`yawIn`**: degrees, positive turns the controller toward the body for either hand (tracking yaw `-yawIn` on the
  left, `+yawIn` on the right), in tracking space like `yaw`: the hands mirror around the body's forward, the
  head's only at head yaw 0 (kept so after the live check). Exclusive with `yaw`, same range; pitch falls back to the ready pitch. No new answer
  fields: the hand's `yaw` shows the applied tracking yaw.
- **Client**: `Hands.place(..., head_offset=None, yaw_in=None)` passes both through; the server validates.
- Moving the flashlight suite onto these is a follow-up in that repo.

## Acceptance

Unit tests for the target math in the pure-logic part. Bridge tool fallback synced. Live check in FO4VR: the same
offset and inward yaw place each hand mirrored around the head; `docs/FALLOUT4.md` records it.
