"""Fallout 4 (and Fallout 4 VR) game setup: a game in a test cell, started from the main menu or reused, then settled.

A cell is named by the editor ID of an interior cell: GetInCell takes no other, and one it does not know does not
compile (DevbenchError). Nothing here prints: each call returns what it did and the dialogs it closed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from devbench.checks import RequirementError
from devbench.client import Devbench, DevbenchError
from devbench.console import console_number
from devbench.menus import close_dialogs, open_menus
from devbench.waits import wait_until

# the wait after each answered message box, as close_dialogs takes it, when the poll interval is longer
_DIALOG_PAUSE = 0.5


@dataclass(frozen=True)
class Settled:
    """
    What settle did: the dialogs it closed (what each said), and whether the game went quiet (False: it was still
    popping up dialogs at the limit).
    """

    dialogs: list[str]
    quiet: bool


@dataclass(frozen=True)
class Entered:
    """
    What enter_game did: started is False when it reused a game already in the cell; dialogs holds every dialog it
    closed; quiet is the settle's outcome after a start, None on a reuse (nothing was settled).
    """

    started: bool
    dialogs: list[str]
    quiet: bool | None


def _player_in(bench: Devbench, cell: str) -> bool:
    """Whether the console's GetInCell says the player is in the cell (by its editor ID)."""
    return int(console_number(bench, f"player.GetInCell {cell}")) == 1


def in_cell(bench: Devbench, cell: str) -> bool:
    """
    Whether a game is loaded with the player in the cell (by its editor ID). False at the main menu, where the player
    exists too and GetInCell reads whatever it last held.
    """
    if "MainMenu" in open_menus(bench):
        return False
    return _player_in(bench, cell)


def settle(bench: Devbench, quiet: float = 10, limit: float = 120, interval: float = 1.0) -> Settled:
    """
    Wait until no message box has popped up for quiet seconds, answering each one that does, as a new game's mods
    pop them up while their quests start. Gives up after limit seconds with Settled.quiet False; that is no error.
    """
    pause = min(_DIALOG_PAUSE, interval)
    dialogs: list[str] = []
    start = time.monotonic()
    quiet_since = start
    while True:
        closed = close_dialogs(bench, pause=pause)
        now = time.monotonic()
        if closed:
            dialogs.extend(closed)
            quiet_since = now
        elif now - quiet_since >= quiet:
            return Settled(dialogs, True)
        if now - start >= limit:
            return Settled(dialogs, False)
        time.sleep(interval)


def enter_game(
    bench: Devbench,
    cell: str = "QASmoke",
    timeout: float = 300,
    quiet: float = 10,
    limit: float = 120,
    interval: float = 1.0,
) -> Entered:
    """
    A game in the cell, so nothing a test does reaches a save. From the main menu: coc to it, wait up to timeout
    seconds for the HUD with no MainMenu or LoadingMenu, then settle (quiet, limit). A game already in the cell is
    reused; another loaded game, or none (mid-load), raises RequirementError. Dialogs are answered throughout.
    """
    pause = min(_DIALOG_PAUSE, interval)
    menus = open_menus(bench)
    # the player exists at the main menu too: the main menu is what tells it from a game
    if "MainMenu" not in menus:
        if "LoadingMenu" in menus or not bench.tool("inspect", kind="state")["playerLoaded"]:
            raise RequirementError(
                f"the game is neither at the main menu nor in a game (open menus: {menus}): "
                "wait for the load to end, or quit to the main menu"
            )
        if not _player_in(bench, cell):
            raise RequirementError(
                f"a game outside {cell} is loaded: quit to the main menu, and a new game is started in {cell}"
            )
        return Entered(False, close_dialogs(bench, pause=pause), None)

    # a coc behind a modal does nothing, so a mod's popup at the main menu is answered first
    dialogs = close_dialogs(bench, pause=pause)
    answer = bench.tool("console", command=f"coc {cell}")
    if answer.get("blocked"):
        raise DevbenchError(
            f"console: coc {cell} was blocked by an open modal (open menus: {open_menus(bench)})",
            tool="console",
            answer=answer,
        )

    def in_game() -> bool:
        dialogs.extend(close_dialogs(bench, pause=pause))
        menus = open_menus(bench)
        return "HUDMenu" in menus and "MainMenu" not in menus and "LoadingMenu" not in menus

    # a coc is neither a new game nor a load to F4SE: the game is in once the main menu and the loading screen are
    # gone and the HUD is up
    wait_until(in_game, timeout, interval=interval, what=f"the game in {cell}")
    settled = settle(bench, quiet=quiet, limit=limit, interval=interval)
    return Entered(True, dialogs + settled.dialogs, settled.quiet)
