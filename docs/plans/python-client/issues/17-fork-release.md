# 17 Release from the fork

Status: needs-triage
Blocked by: 12

Spec: [../spec.md](../spec.md). Needs grilling before work starts: the version scheme is an open decision.

## Why

Releases only happen on `alandtse/devbench`: `release.yaml` gates every job on `github.repository_owner == 'alandtse'`,
builds with xmake (Skyrim only) and packages an `SKSE/Plugins` archive. Neither `rollingrock/devbench` nor this fork
can cut a release, and the fork carries no tags at all (rollingrock's stop at `v1.14.0`). The spec's install line
(`git+https://github.com/ArthurHub/devbench@<tag>#subdirectory=clients/python`) and setuptools-scm both need tags on
the fork. A Fallout 4 / FO4VR release should not have to wait for alandtse or rollingrock.

## What

- A release workflow that runs on this fork (owner `ArthurHub`) without touching alandtse's path, so the file still
  merges upstream cleanly.
- A Fallout build in CI: CMake preset + vcpkg + the `extern/CommonLibF4` submodule, producing `devbench.dll` (+ pdb).
  `_build.yaml` builds only the Skyrim plugin today.
- A Fallout mod archive: `F4SE/Plugins/devbench.dll`, the bridge exe, laid out for MO2.
- A tag on the fork that the Python client's install line and setuptools-scm resolve to.

## Open decisions (grill)

- **Version scheme.** A fork tag `v1.33.0` collides with alandtse's next release of the same number but different
  content. Options: a suffix (`v1.32.0-fo4.1`), a separate tag prefix (`fo4-v1.0.0`, needs setuptools-scm
  `tag_regex`), or own numbering. The DLL's `Version.h` and the Python package should share it.
- **Trigger.** semantic-release on push to the fork's `main` (like upstream), or a manual `workflow_dispatch` / tag push.
- **Version files.** Which of `xmake.lua`, `CMakeLists.txt`, `vcpkg.json` the release rewrites, and how that merges
  with rollingrock's hand bumps on upstream merges.
- **Nexus.** In scope or not.

## Acceptance

A release run on the fork produces a tag and a GitHub Release with the Fallout archive attached; the DLL reports that
version in `ping`; `pip install "devbench-client @ git+https://github.com/ArthurHub/devbench@<tag>#subdirectory=clients/python"`
installs that same version; the Immersive Flashlight and Mods Config requirements lines (tickets 13, 14) move from
their commit pin to that tag.
