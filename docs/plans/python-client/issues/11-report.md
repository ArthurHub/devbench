# 11 HTML report

Status: ready-for-agent
Blocked by: 10

Spec: [../spec.md](../spec.md). Source: both `report.py` files.

## What

`devbench.testing.report`: results by area in `Config.areas` order with the failures first, notes, the dialogs the
run closed, pictures per test; written to `build/e2e/<date>-<time>/index.html` under the mod's root, its link printed
at the end. A mod adds its own sections (the flashlight's placements, Mods Config's perf and sweep) through a section
API (title and rows, or raw HTML). On a failed test: a render-target picture and the log tail since the test started.

## Acceptance

pytester run: the page has each area in order, a failure section, a mod section; a failed test has its picture and
log tail. Light and dark styling kept.
