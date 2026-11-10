# 02 Fallout VR seam, hooks and input tool

Status: ready-for-agent
Blocked by: 01

Real Fallout seam: interfaces from `VR_GetGenericInterface`, hooks installed at kGameLoaded with
per-frame retry, per-slot "closest to runtime" report in `status`, release on kPreLoadGame and
kNewGame. New Fallout `input` tool (`device='vrTrackedSet'`: status, observe, sequence, stop,
releaseAll). Bridge fallback synced.

Done: a raw Sequence moves the Wands live on FO4VR.
