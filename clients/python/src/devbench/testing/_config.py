"""The mod's settings for the plugin: the DEVBENCH object its rootdir conftest defines."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

# the games devbench runs in, as find_port and require name them
_GAMES = ("skyrim", "fallout4")

# the handedness a run can set: the controller that is the primary hand
_HANDEDNESS = ("left", "right")


@dataclass(frozen=True)
class Config:
    """
    What a mod's suite needs: the game (and VR), the mod's devbench tool with the actions its tests call and the
    checkout's version, the files a run changes ((root, glob) pairs, backed up for the run), the mod's log, the report's
    areas by test-file name in run order, and the cell the game runs in. tool None skips the mod check. picture is the
    render target dumped when a test fails (None: no picture); report_dir holds the run folders of the report
    (relative: to the DEVBENCH conftest's folder; None: build/e2e under the first folder up from it with a .git).
    handedness ("left" / "right", VR only) is set for the run and the player's put back after; None leaves it alone.
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
    picture: int | None = None
    report_dir: str | os.PathLike[str] | None = None
    handedness: str | None = None

    def __post_init__(self) -> None:
        if self.game not in _GAMES:
            raise ValueError(f"unknown game {self.game!r}: expected 'skyrim' or 'fallout4'")
        if self.handedness is not None and self.handedness not in _HANDEDNESS:
            raise ValueError(f"unknown handedness {self.handedness!r}: expected 'left', 'right' or None")
        if self.handedness is not None and not self.vr:
            raise ValueError("handedness needs vr=True: only VR has one")

    def expected_version(self) -> str | None:
        """The checkout's version the mod must report: version itself, or what it returns when it is a callable."""
        return self.version() if callable(self.version) else self.version
