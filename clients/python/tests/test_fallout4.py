"""Fallout 4 game setup: a game entered from the main menu or reused, refused elsewhere, and settled."""

import pytest

from devbench import DevbenchError, RequirementError
from devbench.games.fallout4 import Entered, Settled, enter_game, in_cell, settle

# a poll fast enough that a test waits milliseconds
FAST = {"interval": 0.01}


class FakeGame:
    """
    A scripted game behind the menu, inspect and console tools. menus are the open menus; cell is the player's cell.
    A coc shows LoadingMenu for load_polls menu lists, then the HUD in the target cell. boxes is the queue of open
    message boxes; pop_up(n) is asked at the nth menu list and returns a box text to open, or None. commands records
    the console commands.
    """

    def __init__(
        self,
        menus=("MainMenu",),
        cell=None,
        player_loaded=True,
        boxes=(),
        blocked=False,
        load_polls=2,
        pop_up=None,
        loads=True,
    ):
        self.menus = list(menus)
        self.cell = cell
        self.player_loaded = player_loaded
        self.boxes = list(boxes)
        self.blocked = blocked
        self.load_polls = load_polls
        self.pop_up = pop_up
        self.loads = loads
        self.commands = []
        self.lists = 0
        self._loading = None

    def install(self, fake):
        fake.tools["menu"] = self.menu
        fake.tools["inspect"] = lambda args: {"ok": True, "playerLoaded": self.player_loaded}
        fake.tools["console"] = self.console

    def menu(self, args):
        action = args["action"]
        if action == "list":
            self.lists += 1
            self._advance_load()
            if self.pop_up and (text := self.pop_up(self.lists)):
                self.boxes.append(text)
            return {"ok": True, "openMenus": list(self.menus), "messageBoxOpen": bool(self.boxes)}
        if action == "describe":
            return {"ok": True, "headerText": "", "bodyText": self.boxes[0]}
        if action == "accept":
            self.boxes.pop(0)
            return {"ok": True}
        raise AssertionError(f"unexpected menu action {action}")

    def _advance_load(self):
        if self._loading is None:
            return
        target, left = self._loading
        if left > 0:
            self.menus = ["LoadingMenu"]
            self._loading = (target, left - 1)
        elif self.loads:
            self.menus = ["HUDMenu"]
            self.cell = target
            self._loading = None

    def console(self, args):
        command = args["command"]
        self.commands.append(command)
        verb, _, operand = command.partition(" ")
        if verb == "player.GetInCell":
            value = 1 if operand == self.cell else 0
            return {"ok": True, "compiled": True, "captured": True, "lines": [f"GetInCell >> {value:.2f}"]}
        if verb == "coc":
            if self.blocked:
                return {"ok": True, "executed": True, "captured": False, "blocked": True}
            self._loading = (operand, self.load_polls)
            return {"ok": True, "executed": True, "captured": False, "blocked": False}
        raise AssertionError(f"unexpected console command {command}")


def test_enter_game_from_the_main_menu_starts_one_in_the_cell(fake, bench):
    game = FakeGame(pop_up=lambda n: "Mod installed" if n == 3 else None)
    game.install(fake)

    entered = enter_game(bench, quiet=0.05, **FAST)

    assert entered == Entered(started=True, dialogs=["Mod installed"], quiet=True)
    assert game.commands == ["coc QASmoke"]
    assert game.cell == "QASmoke"


def test_enter_game_answers_a_main_menu_dialog_before_the_coc(fake, bench):
    game = FakeGame(boxes=["Welcome"])
    game.install(fake)

    entered = enter_game(bench, cell="TestCell", quiet=0.05, **FAST)

    assert entered.started
    assert entered.dialogs == ["Welcome"]
    assert game.commands == ["coc TestCell"]


def test_enter_game_raises_when_the_coc_is_blocked(fake, bench):
    FakeGame(blocked=True).install(fake)

    with pytest.raises(DevbenchError, match="blocked"):
        enter_game(bench, **FAST)


def test_enter_game_raises_when_the_hud_never_comes(fake, bench):
    FakeGame(loads=False).install(fake)

    with pytest.raises(TimeoutError, match="the game in QASmoke"):
        enter_game(bench, timeout=0.1, **FAST)


def test_enter_game_reuses_a_game_in_the_cell(fake, bench):
    game = FakeGame(menus=["HUDMenu"], cell="QASmoke", boxes=["Hello"])
    game.install(fake)

    entered = enter_game(bench, **FAST)

    assert entered == Entered(started=False, dialogs=["Hello"], quiet=None)
    assert game.commands == ["player.GetInCell QASmoke"]


def test_enter_game_refuses_a_game_in_another_cell(fake, bench):
    game = FakeGame(menus=["HUDMenu"], cell="SanctuaryExt")
    game.install(fake)

    with pytest.raises(RequirementError, match="outside QASmoke.*quit to the main menu"):
        enter_game(bench, **FAST)
    assert not any(command.startswith("coc") for command in game.commands)


@pytest.mark.parametrize(
    ("menus", "player_loaded"), [(["LoadingMenu"], True), (["FaderMenu"], False)], ids=["loading", "no-player"]
)
def test_enter_game_refuses_neither_menu_nor_game(fake, bench, menus, player_loaded):
    game = FakeGame(menus=menus, player_loaded=player_loaded)
    game.install(fake)

    with pytest.raises(RequirementError, match="neither at the main menu nor in a game"):
        enter_game(bench, **FAST)
    assert game.commands == []


def test_settle_returns_once_quiet(fake, bench):
    FakeGame(menus=["HUDMenu"]).install(fake)

    assert settle(bench, quiet=0.05, limit=5, **FAST) == Settled(dialogs=[], quiet=True)


def test_settle_waits_out_the_quiet_period_after_each_dialog(fake, bench):
    FakeGame(menus=["HUDMenu"], pop_up=lambda n: f"popup {n}" if n in (2, 4) else None).install(fake)

    settled = settle(bench, quiet=0.05, limit=5, **FAST)

    assert settled == Settled(dialogs=["popup 2", "popup 4"], quiet=True)


def test_settle_gives_up_at_the_limit(fake, bench):
    FakeGame(menus=["HUDMenu"], pop_up=lambda n: f"popup {n}").install(fake)

    settled = settle(bench, quiet=0.2, limit=0.1, **FAST)

    assert not settled.quiet
    assert settled.dialogs


def test_in_cell_is_false_at_the_main_menu(fake, bench):
    game = FakeGame(cell="QASmoke")
    game.install(fake)

    assert not in_cell(bench, "QASmoke")
    assert game.commands == []


def test_in_cell_reads_get_in_cell(fake, bench):
    FakeGame(menus=["HUDMenu"], cell="QASmoke").install(fake)

    assert in_cell(bench, "QASmoke")
    assert not in_cell(bench, "SanctuaryExt")
