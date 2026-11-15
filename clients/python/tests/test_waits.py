"""wait_until: returns the first true value, or raises TimeoutError naming the condition."""

import pytest

from devbench import wait_until


def test_returns_the_first_true_value():
    answers = iter([None, 0, {"found": 1}])

    assert wait_until(lambda: next(answers), timeout=5.0, interval=0.0) == {"found": 1}


def test_checks_once_with_a_zero_timeout():
    assert wait_until(lambda: "ready", timeout=0.0) == "ready"


def test_times_out_with_the_condition_named():
    calls = []

    def never():
        calls.append(1)
        return False

    with pytest.raises(TimeoutError, match="the menu did not hold within 0.05 s"):
        wait_until(never, timeout=0.05, interval=0.01, what="the menu")

    assert len(calls) > 1
