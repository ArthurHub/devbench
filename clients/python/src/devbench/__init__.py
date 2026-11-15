"""Python client for devbench's REST port: call a running game's tools from a script, a REPL or a test.

Importing the package never imports pytest; the opt-in pytest plugin lives in devbench.testing.
"""

from importlib.metadata import PackageNotFoundError, version

from devbench.client import Devbench, DevbenchError, ModTool, find_port
from devbench.events import Events
from devbench.waits import wait_until

try:
    __version__ = version("devbench-client")
except PackageNotFoundError:  # a source tree on sys.path that was never installed
    __version__ = "0.0.0"

__all__ = ["Devbench", "DevbenchError", "Events", "ModTool", "__version__", "find_port", "wait_until"]
