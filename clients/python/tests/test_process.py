"""Quitting the game: the quit tool or qqq, then waiting for the process or the port to go."""

import subprocess
import sys
import threading

import pytest
from fake_devbench import HANG_UP

from devbench import DevbenchError, quit_game, wait_gone

# the console tool's answer to a command that leaves the world: queued for a later frame, never captured
_QUEUED = {"ok": True, "executed": True, "captured": False, "queued": True}


def _later(seconds, action):
    """Run action on a timer thread after seconds."""
    timer = threading.Timer(seconds, action)
    timer.daemon = True
    timer.start()
    return timer


@pytest.fixture
def child():
    """A real process that runs until killed, standing in for the game's."""
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    yield process
    process.kill()
    process.wait()


def test_quit_game_returns_once_the_game_stops(fake, bench):
    def qqq(args):
        _later(0.1, fake.stop)
        return {**_QUEUED, "command": args["command"]}

    fake.tools["console"] = qqq

    quit_game(bench, timeout=5)

    assert ("POST", "/api/tool/console", {"command": "qqq"}) in fake.calls


def test_quit_game_uses_the_quit_tool_and_its_pid(fake, bench, child):
    fake.health = {"ok": True, "pid": 1}
    fake.tools["console"] = lambda args: _QUEUED

    def quit_tool(args):
        _later(0.1, child.kill)
        return {"ok": True, "pid": child.pid, "quitting": True, "killAfterMs": args.get("killAfterMs", 0)}

    fake.tools["quit"] = quit_tool

    quit_game(bench, timeout=5, kill_after=30)

    assert ("POST", "/api/tool/quit", {"killAfterMs": 30000}) in fake.calls
    assert not any(path == "/api/tool/console" for _, path, _ in fake.calls)


def test_quit_game_arms_no_watchdog_by_default(fake, bench):
    def quit_tool(args):
        _later(0.1, fake.stop)
        return {"ok": True, "quitting": True}

    fake.tools["quit"] = quit_tool

    quit_game(bench, timeout=5)

    assert ("POST", "/api/tool/quit", {}) in fake.calls


def test_quit_game_times_out_while_the_port_answers(fake, bench):
    fake.tools["console"] = lambda args: _QUEUED

    with pytest.raises(DevbenchError, match="port .* still answers"):
        quit_game(bench, timeout=0.5)


def test_quit_game_on_a_gone_game_returns_at_once(fake, bench):
    fake.stop()

    quit_game(bench, timeout=5)

    assert not any(path == "/api/tool/console" for _, path, _ in fake.calls)


def test_quit_game_goes_on_waiting_when_qqq_drops_the_connection(fake, bench):
    def qqq(args):
        fake.stop()
        return HANG_UP

    fake.tools["console"] = qqq

    quit_game(bench, timeout=5)


def test_quit_game_waits_for_the_process_named_by_health(fake, bench, child):
    fake.health = {"ok": True, "pid": child.pid}
    fake.tools["console"] = lambda args: _QUEUED
    _later(0.3, child.kill)

    quit_game(bench, timeout=5)

    assert child.poll() is not None


def test_wait_gone_times_out_while_the_process_runs(fake, child):
    fake.stop()

    with pytest.raises(DevbenchError, match=f"process {child.pid} is still running; port {fake.port} is closed"):
        wait_gone(fake.port, child.pid, timeout=0.5)


def test_wait_gone_reads_the_pid_from_health(fake, child):
    fake.health = {"ok": True, "pid": child.pid}

    with pytest.raises(DevbenchError, match=f"process {child.pid} is still running"):
        wait_gone(fake.port, timeout=0.5)


def test_wait_gone_with_a_gone_port_and_no_pid_returns(fake):
    fake.stop()

    wait_gone(fake.port, timeout=0)
