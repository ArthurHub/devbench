"""Fixtures shared by the client's unit tests."""

from collections.abc import Iterator

import pytest
from fake_devbench import FakeDevbench

from devbench import Devbench

# the plugin's tests run inner pytest sessions
pytest_plugins = ["pytester"]


@pytest.fixture
def fake() -> Iterator[FakeDevbench]:
    """A fake devbench on a free port, stopped after the test."""
    server = FakeDevbench()
    yield server
    server.close()


@pytest.fixture
def bench(fake: FakeDevbench) -> Iterator[Devbench]:
    """A client connected to the fake devbench."""
    with Devbench(fake.port, timeout=5.0) as client:
        yield client
