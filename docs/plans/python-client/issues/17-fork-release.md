# 17 Release from the fork

Status: ready-for-agent
Blocked by: 12

Spec: [../spec.md](../spec.md).

## Why

Releases only happen on `alandtse/devbench`: `release.yaml` gates every job on `github.repository_owner == 'alandtse'`,
builds with xmake (Skyrim only) and packages an `SKSE/Plugins` archive. Neither `rollingrock/devbench` nor this fork
can cut a release, and the fork carries no tags at all (rollingrock's stop at `v1.14.0`, alandtse is at `v1.36.0`).
The spec's install line and setuptools-scm both need tags on the fork, and the client's CI today resolves
`1.14.1.devN` from rollingrock's tags while the DLL reports `1.32.0`. A Fallout 4 / FO4VR release should not have to
wait for alandtse or rollingrock.

## Decisions

- **Version scheme.** The fork has its own numbering under the tag prefix `fo4-v`; the first release is `fo4-v1.0.0`.
  The DLL's displayed version and the Python package share it.
- **API build number stays upstream's.** `DEVBENCH_BUILD_NUMBER` (what `GetBuildNumber()` returns, which mods compare
  against `10500` / `12000` before calling late vtable slots) keeps coming from the version in the files (1.32.0 →
  13200). Feeding it `1.0.0` would make every consumer skip those slots. The fork never appends API slots on its own.
- **Version files are never rewritten.** `xmake.lua`, `CMakeLists.txt` and `vcpkg.json` keep upstream's number, so
  rollingrock's hand bumps merge cleanly. `CMakeLists.txt` takes an override for `VERSION_STRING` only; `MAJOR` /
  `MINOR` / `PATCH` (build number, F4SE plugin-info version) stay the file's. `Version.h.in` and `xmake.lua` are
  untouched.
- **Local builds.** Without the override, CMake derives the string at configure time from
  `git describe --match "fo4-v*"`, in setuptools-scm's format (`1.0.1.dev5+gabc1234`), so `ping` and `pip show` agree
  on the same commit. No fo4 tag or no git: the file's value. The string refreshes only on reconfigure.
- **Trigger.** Pushing a `fo4-v*` tag. The workflow fails early unless the tag is exactly `fo4-vX.Y.Z` and the tagged
  commit is on `main`.
- **Workflow files.** New `release-fallout.yaml` (gated on `github.repository_owner == 'ArthurHub'`) and a reusable
  `_build-fallout.yaml`; `release.yaml`, `_build.yaml` and `.releaserc` stay as upstream has them. The Fallout build
  runs at release only, not on every push.
- **CI build.** The `fallout4-vs2022` preset (v143) with vcpkg and the `extern/CommonLibF4` submodule; local work keeps
  vs2026. Confirm the runner's toolchains when implementing.
- **Archive.** `devbench-fo4-vX.Y.Z.7z`: `F4SE/Plugins/devbench.dll` + `.pdb`, `F4SE/Plugins/devbench/devbench-bridge.exe`.
  No Skyrim recordings, no config file, no `DevBenchAPI.h`. One archive serves Fallout 4 and FO4VR.
- **Release.** Created as a draft with the archive attached; notes are the tag's annotation if it has one, else the
  commit subjects since the previous `fo4-v*` tag. Publishing the draft is manual.
- **Python.** `pyproject.toml` gets a `tag_regex` and a describe command matching `fo4-v*`; `python-client.yaml` drops
  the rollingrock tag fetch. Until the first tag, setuptools-scm gives `0.1.devN`, which passes the `0.0.0` check.
  Install stays the `git+…@<tag>#subdirectory=clients/python` line: no wheel on the Release, no PyPI.
- **Out of scope.** Nexus (later, a job after the Release reusing `nexus-upload.yaml`), the bridge's own `0.1.0`
  version, an `apiBuild` field in `ping`.

## Work

On the `python-client` branch, one staged commit at a time:

1. `feat(fallout4)`: the `VERSION_STRING` override and the `git describe` default in `CMakeLists.txt`.
2. `feat(python)`: the `fo4-v` tag regex and describe command; `python-client.yaml` stops fetching rollingrock's tags.
3. `ci(fallout4)`: `_build-fallout.yaml` and `release-fallout.yaml`.
4. `docs(fallout4)`: a "Releasing" section in `docs/FALLOUT4.md` (tagging, archive contents, the build-number rule);
   the spec's and client README's install line move to `@fo4-v1.0.0`.

Then `main` fast-forwards to `python-client` and `fo4-v1.0.0` is pushed on `main`.

## Acceptance

Pushing `fo4-v1.0.0` produces a draft GitHub Release with the Fallout archive attached. The archive's DLL, deployed to
the MO2 `mods\DevBench` folder, reports `1.0.0` in `ping` on FO4VR, and `GetBuildNumber()` still returns 13200;
`pip install "devbench-client @ git+https://github.com/ArthurHub/devbench@fo4-v1.0.0#subdirectory=clients/python"`
installs `1.0.0`. The live check (runtime, date) is recorded in `docs/FALLOUT4.md`.

## Follow-ups

Moving the Immersive Flashlight and Mods Config requirements lines from their commit pin to `@fo4-v1.0.0` happens in
those repos, under tickets 13 and 14.
