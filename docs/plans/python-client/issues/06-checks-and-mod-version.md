# 06 Checks and the mod version check

Status: ready-for-agent
Blocked by: 02

Spec: [../spec.md](../spec.md). Source: `_connect` and `_check_mod` in the flashlight conftest.

## What

`devbench.checks`: `RequirementError`; `require(bench, game, vr)` from `ping`; `require_tools(bench, names)`;
`require_actions(mod_tool, actions)` from the mod tool's `health`; `require_version(mod_tool, expected)`. Each message
says what to do ("deploy this build").

## Acceptance

Unit tests: wrong game, not VR, missing tool, missing action, version mismatch each raise with a clear message; all
present passes.
