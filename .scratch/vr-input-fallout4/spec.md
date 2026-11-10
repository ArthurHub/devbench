# VR input on Fallout 4 VR

Status: ready-for-agent

E2E tests drive the VR Controllers on Fallout 4 VR (poses and buttons), so a test can exercise
features that react to hand position and button presses. Terms follow [GLOSSARY.md](../../GLOSSARY.md).

## Acceptance

The Immersive Flashlight gesture runs live on FO4VR through devbench alone: Reach puts the Wand
next to `hmdNode`, `press` holds the button, and the flashlight toggles.

## Decisions

- **Contract**: Skyrim's `vrTrackedSet` is ported unchanged (same `input` tool shape, actions,
  Frame JSON and contract version). The whole Tracked set is replaced, as on Skyrim. Raw
  `sequence` plus `reach`. Recording and replay stay Skyrim-only.
- **Code**: the game-independent parts (Sequence manager, playback, Reach orchestration, OpenVR
  hook bodies) move to `src/core/` behind a free-function VR seam. Skyrim is refactored onto them.
  Fallout gets an `input` tool with only `device='vrTrackedSet'`.
- **OpenVR on Fallout**: the IVRSystem_019 / IVRCompositor_022 `openvr.h` is vendored for types.
  Interfaces come from `VR_GetGenericInterface` looked up at runtime on the loaded
  `openvr_api.dll` (the real objects; FO4VRTools' proxies stay above them). No link dependency.
- **Hook position**: hooks install at kGameLoaded, retrying each frame until OpenVR is up, so
  devbench patches the slots before CommonFramework (which patches one frame later). Injected
  input then passes through other mods' controller hooks like real input. `status` reports per
  slot whether devbench sits closest to the runtime.
- **Lifecycle**: an active Sequence is released on kPreLoadGame and kNewGame.
- **Reach on Fallout**: reads the Wands (`vrNodes` primary/secondary wand, mapped to physical
  left/right through the left-handed setting). Targets resolve by name: `vrNodes` slot names
  (as the `nodes` tool names them), then the first-person skeleton, then the body skeleton FRIK
  drives. Skyrim keeps reading its hand bones.
- **Buttons**: a `press` action overlays named buttons (with matching axis values) on the active
  Sequence for a duration, same owner, refused when nothing is active.

## Done

- Live FO4VR pass of the acceptance scenario; `docs/FALLOUT4.md` records it.
- Unit tests for the moved pure logic; Skyrim compiles and its unit tests pass. Skyrim is not
  re-run live after the refactor, and the docs say so.
- Bridge fallback synced in every commit that changes a tool.

## Follow-up (other repo)

The flashlight's gesture test switches to devbench Reach + `press`, gated on a devbench build or
tool check.
