"""The opt-in pytest plugin for in-game end-to-end tests. A mod's rootdir conftest turns it on and configures it:

    pytest_plugins = ["devbench.testing"]
    DEVBENCH = devbench.testing.Config(game="fallout4", vr=True, tool="mymod", ...)

pytest registers this module itself, so the hooks and fixtures are re-exported here.
"""

from devbench.testing._config import Config
from devbench.testing._plugin import (
    bench,
    events,
    game,
    log_mark,
    mod,
    pytest_addoption,
    pytest_collection_modifyitems,
    pytest_configure,
    pytest_sessionstart,
    report,
)
from devbench.testing._record import Record, Result

__all__ = [
    "Config",
    "Record",
    "Result",
    "bench",
    "events",
    "game",
    "log_mark",
    "mod",
    "pytest_addoption",
    "pytest_collection_modifyitems",
    "pytest_configure",
    "pytest_sessionstart",
    "report",
]
