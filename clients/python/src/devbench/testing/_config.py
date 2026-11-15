"""The mod's settings for the plugin: the DEVBENCH object its rootdir conftest defines."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

# the games devbench runs in, as find_port and require name them
_GAMES = ("skyrim", "fallout4")


@dataclass(frozen=True)
class Config:
    """
    What a mod's suite needs: the game (and VR), the mod's devbench tool with the actions its tests call and the
    checkout's version, the files a run changes ((root, glob) pairs, backed up for the run), the mod's log, the report's
    areas by test-file name in run order, and the cell the game runs in. tool None skips the mod check.
    """

    game: str
    vr: bool
    tool: str | None = None
    actions: Sequence[str] = ()
    version: str | Callable[[], str] | None = None
    backup: Sequence[tuple[str, str]] = ()
    log: str | None = None
    areas: Mapping[str, str] = field(default_factory=dict)
    title: str | None = None
    cell: str = "QASmoke"

    def __post_init__(self) -> None:
        if self.game not in _GAMES:
            raise ValueError(f"unknown game {self.game!r}: expected 'skyrim' or 'fallout4'")

    def expected_version(self) -> str | None:
        """The checkout's version the mod must report: version itself, or what it returns when it is a callable."""
        return self.version() if callable(self.version) else self.version
