# 07 Fallout 4 game setup

Status: resolved
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

## Verified

FO4VR, 2026-11-15: from the main menu `enter_game` started a game in QASmoke in 20 s, answering three mod dialogs
during the load and settle, and settled quiet; a second call reused it; `in_cell` was False at the main menu, True in
QASmoke, False for `Vault111Cryo`; `enter_game(cell="Vault111Cryo")` in QASmoke raised `RequirementError`. The cell
must be an interior cell's editor ID: `GetInCell` does not compile for an exterior or unknown one.
