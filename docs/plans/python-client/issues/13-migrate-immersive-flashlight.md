# 13 Move Immersive Flashlight's suite onto the client

Status: ready-for-agent
Blocked by: 09, 10, 11

Spec: [../spec.md](../spec.md). Work is in the `F4VR-ImmersiveFlashlight` repo, against an editable install.

## What

Replace `devbench.py`, `backup.py`, `report.py` and the shared conftest code with the package; `controllers.py` uses
`Hands`; the conftest keeps the mod's fixtures (`loadout`, `flashlight`, `weapon`) and defines `DEVBENCH`. The
requirements line pins a devbench commit on the fork
(`git+https://github.com/ArthurHub/devbench@<sha>#subdirectory=clients/python`): the fork has no tags until ticket 17,
which moves the pin to a tag.

## Acceptance

The full suite runs in FO4VR with the same results as before the move, and the report shows the same areas and
placements. Gaps the move exposes in the client go back as fixes to the earlier tickets.
