# 14 Move Mods Config's suite onto the client

Status: ready-for-agent
Blocked by: 13

Spec: [../spec.md](../spec.md). Work is in the `F4VR-Mods-Config` repo.

## What

Same as 13, including the commit pin on the fork until ticket 17 releases `fo4-v1.0.0`, then `@fo4-v1.0.0`. `stored.py`'s INI and TOML readers and the panel
snapshot stay in the mod; its perf and sweep sections use the report's section API.

## Acceptance

The full suite runs in FO4VR with the same results as before the move.
