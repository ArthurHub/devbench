# 01 Move VR input into core

Status: ready-for-agent

Move the Sequence manager, the `vrTrackedSet` handler, the OpenVR hook bodies and the Reach
orchestration from `src/platform/skyrim/` into `src/core/`, behind a free-function VR seam.
Skyrim implements the seam with its current engine calls. Fallout gets stub seam definitions
and the vendored `openvr.h` so it keeps building. No behaviour change on Skyrim.

Done: both builds compile, unit tests pass.
