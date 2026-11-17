# 17 Release from the fork

Status: ready-for-human
Blocked by: 12

Spec: [../spec.md](../spec.md).

## Why

Releases only happen on `alandtse/devbench`: `release.yaml` gates every job on `github.repository_owner == 'alandtse'`,
builds with xmake (Skyrim only) and packages an `SKSE/Plugins` archive. Neither `rollingrock/devbench` nor this fork
can cut a release, and the fork carries no tags at all (rollingrock's stop at `v1.14.0`, alandtse is at `v1.36.0`).
The spec's install line and setuptools-scm both need tags on the fork, and the client's CI today resolves
`1.14.1.devN` from rollingrock's tags while the DLL reports `1.32.0`. A Fallout 4 / FO4VR release should not have to
wait for alandtse or rollingrock, and must not touch the Skyrim release.

## Decisions

- **Least divergence from upstream.** Every choice below keeps upstream's files as they are, so merges stay clean;
  the fork adds files, it does not change upstream's.
- **Version scheme.** No numbering of its own: a Fallout release uses the version already in `CMakeLists.txt`
  (`1.32.0` today) and is tagged `fo4-vX.Y.Z`. The prefix only keeps the tag apart from the Skyrim release's
  `vX.Y.Z`, which already exists upstream for the same numbers. The first release is `fo4-v1.32.0`.
- **The version is never bumped for a Fallout release.** It is also `DEVBENCH_BUILD_NUMBER` (what `GetBuildNumber()`
  returns, which mods compare against `10500` / `12000` before calling late vtable slots); a fork-made number could
  claim a slot the DLL lacks. It moves only with upstream's bumps of `xmake.lua` / `CMakeLists.txt` / `vcpkg.json`.
  A second Fallout release on the same number waits for that bump.
- **Displayed version.** `ping` and the load log show the file's version, unchanged (`CMakeLists.txt` is upstream's).
  The Python package shows the tag's on the tag (equal) and `X.Y.(Z+1).devN+g<hash>` past it.
- **Trigger.** Pushing a `fo4-v*` tag. The workflow fails early unless the tag is exactly `fo4-vX.Y.Z`, the tagged
  commit is on `main`, and X.Y.Z is `CMakeLists.txt`'s `VERSION`.
- **Workflow files.** New `release-fallout.yaml` and a reusable `_build-fallout.yaml`; `release.yaml`, `_build.yaml`
  and `.releaserc` stay as upstream has them. No repository-owner gate: the workflow only runs on a `fo4-v*` tag push,
  so any repository carrying it (rollingrock, after a merge) can cut a Fallout release. The two release pipelines are
  independent: `release.yaml` runs on alandtse's `main` pushes, `release-fallout.yaml` on `fo4-v*` tags. The Fallout
  build runs at release only, not on every push; `_build-fallout.yaml` also takes a manual dispatch for a trial build
  before tagging. The release also checks the Python client resolves the tag to the same version.
- **CI build.** The `fallout4-vs2022` preset (v143) with vcpkg and the `extern/CommonLibF4` submodule; local work keeps
  vs2026.
- **Archive.** `devbench-fo4-vX.Y.Z.7z`: `F4SE/Plugins/devbench.dll` + `.pdb`, `F4SE/Plugins/devbench/devbench-bridge.exe`.
  No Skyrim recordings, no config file, no `DevBenchAPI.h`. One archive serves Fallout 4 and FO4VR.
- **Release.** Created as a draft with the archive attached; notes are the tag's annotation if it has one, else the
  commit subjects since the previous `fo4-v*` tag. Publishing the draft is manual.
- **Python.** `pyproject.toml` sets `scm.git.describe_command` to `git describe --match fo4-v*` (needs
  setuptools-scm 9; 8.x rejects the table). No `tag_regex`: setuptools-scm 10 deprecates it and the default regex
  already strips `fo4-`. `python-client.yaml` drops the rollingrock tag fetch. Until the first tag, setuptools-scm
  gives `0.0.1.devN`, which passes the `0.0.0` check. Install stays the `git+…@<tag>#subdirectory=clients/python` line: no wheel on the Release, no PyPI.
- **Out of scope.** Nexus (later, a job after the Release reusing `nexus-upload.yaml`), the bridge's own `0.1.0`
  version, an `apiBuild` field in `ping`.

## Work

On the `python-client` branch, one staged commit at a time:

1. `feat(fallout4)`: the `VERSION_STRING` override and the `git describe` default in `CMakeLists.txt`.
2. `feat(python)`: the `fo4-v` tag regex and describe command; `python-client.yaml` stops fetching rollingrock's tags.
3. `ci(fallout4)`: `_build-fallout.yaml` and `release-fallout.yaml`.
4. `docs(fallout4)`: a "Releasing" section in `docs/FALLOUT4.md` (tagging, archive contents, the build-number rule);
   the spec's and client README's install line move to the release tag.
5. `ci(fallout4)`: drop the fork's own numbering for the file's version under the `fo4-v` prefix: `CMakeLists.txt`
   back to upstream's, `cmake/fork-version.cmake` gone, no version input to the build, the tag checked against
   `CMakeLists.txt`, no owner gate.

Then `main` fast-forwards to `python-client` and `fo4-v1.32.0` is pushed on `main`.

Done (2026-11-17): the five commits. Checked locally: the client's CI steps pass. Not yet run on GitHub: neither
workflow, nor actionlint. Left: fast-forward `main`, optionally the trial build, push the tag, the live check below.

## Acceptance

Pushing `fo4-v1.32.0` produces a draft GitHub Release with the Fallout archive attached; a tag whose X.Y.Z is not
`CMakeLists.txt`'s version fails before building. The archive's DLL, deployed to the MO2 `mods\DevBench` folder,
reports `1.32.0` in `ping` on FO4VR, and `GetBuildNumber()` returns 13200;
`pip install "devbench-client @ git+https://github.com/ArthurHub/devbench@fo4-v1.32.0#subdirectory=clients/python"`
installs `1.32.0`. The live check (runtime, date) is recorded in `docs/FALLOUT4.md`.

## Follow-ups

Moving the Immersive Flashlight and Mods Config requirements lines from their commit pin to `@fo4-v1.32.0` happens in
those repos, under tickets 13 and 14.
