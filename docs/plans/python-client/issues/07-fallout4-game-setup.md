# 07 Fallout 4 game setup

Status: ready-for-agent
Blocked by: 04

Spec: [../spec.md](../spec.md). Source: `_start_game`, `wait_for_game`, `_settle` in both conftests.

## What

`devbench.games.fallout4`: `in_cell(bench, cell)`, `enter_game(bench, cell="QASmoke")` (from the main menu: `coc`,
wait for the HUD up with no MainMenu or LoadingMenu, closing dialogs; already in that cell: reuse; another cell
loaded: raise), `settle(bench, quiet=10, limit=120)`. Returns what it did and the dialogs it closed, so
the plugin can report them; no printing or report coupling here.

## Acceptance

Unit tests with a scripted fake: from the main menu, already in the cell, in another cell (raises), settle waits for
the quiet period and gives up at the limit. Live check in FO4VR from the main menu.
