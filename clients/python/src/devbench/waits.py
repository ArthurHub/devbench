"""Polling: wait for a condition of the running game to hold."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def wait_until(check: Callable[[], T], timeout: float, interval: float = 0.1, what: str = "the condition") -> T:
    """
    Call check until it returns a true value, and return that value; raise TimeoutError after timeout seconds.
    check runs at least once, also with a timeout of 0; what names the condition in the error.
    """
    deadline = time.monotonic() + timeout
    while True:
        value = check()
        if value:
            return value
        if time.monotonic() > deadline:
            raise TimeoutError(f"{what} did not hold within {timeout} s")
        time.sleep(interval)
