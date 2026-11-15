# 23 Immersive Flashlight adopts the new pieces

Status: ready-for-agent
Blocked by: 18, 19, 20, 21, 22

Spec: [../spec.md](../spec.md). Work is in the `F4VR-ImmersiveFlashlight` repo, against an editable install.

## What

The suite drops its own handedness code and `--left-handed` option (18), the head-axis math and yaw flip (19), its wait
helper and log-warning regex (20), its marker lists, FRIK check, ready wait and test-name parsing (21), and the generic
part of `Loadout` (22). The mod's actions, zone aiming, baseline settings and tests stay. The requirements pin moves to
the devbench commit that has them.

## Acceptance

The full suite runs in FO4VR right-handed and with `--left-handed`, with the same results as before, and the report
shows the same areas and placements. Gaps it exposes go back as fixes to 18-22.
