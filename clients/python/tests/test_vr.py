"""VR hands: the token kept and passed to stop, stop on an exception, a refused stop, the pose arguments, presses."""

import pytest

import devbench.vr
from devbench import DevbenchError, Hands


class _Input:
    """A scripted input tool: pose answers a token, stop and press answer ok or as refuse says."""

    def __init__(self):
        self.calls = []
        self.token = "t1"
        self.refuse = set()
        self.tracked = {"available": True, "ready": True}

    def __call__(self, args):
        self.calls.append(args)
        action = args.get("action")
        if action in self.refuse:
            return 409, {"ok": False, "error": f"{action} refused"}
        if action == "capabilities":
            return {"capabilities": {"vrTrackedSet": self.tracked}}
        if action == "pose":
            return {"controlToken": self.token, "fresh": True, "corrections": 1}
        return {"ok": True}

    def actions(self):
        return [call["action"] for call in self.calls]


@pytest.fixture
def tool(fake):
    script = _Input()
    fake.tools["input"] = script
    return script


@pytest.fixture
def slept(monkeypatch):
    """The waits press made, without waiting."""
    waits = []
    monkeypatch.setattr(devbench.vr.time, "sleep", waits.append)
    return waits


def test_ready_reads_the_vr_tracked_set_capability(bench, tool):
    assert Hands(bench, "e2e").ready()
    tool.tracked = {"available": True, "ready": False}
    assert not Hands(bench, "e2e").ready()


def test_start_takes_the_ready_pose_and_keeps_the_token(bench, tool):
    hands = Hands(bench, "e2e")

    hands.start()

    assert tool.calls == [{"action": "pose", "owner": "e2e", "hands": "ready", "head": "ready"}]
    assert hands.token == "t1"


def test_stop_passes_the_token_and_clears_it(bench, tool):
    hands = Hands(bench, "e2e")
    hands.start()

    hands.stop()
    hands.stop()

    assert tool.calls[1:] == [{"action": "stop", "owner": "e2e", "controlToken": "t1"}]
    assert hands.token is None


def test_stop_without_a_hold_sends_nothing(bench, tool):
    Hands(bench, "e2e").stop()

    assert tool.calls == []


def test_a_refused_stop_is_ignored(bench, tool):
    hands = Hands(bench, "e2e")
    hands.start()
    tool.refuse.add("stop")

    hands.stop()

    assert hands.token is None


def test_with_starts_and_stops(bench, tool):
    with Hands(bench, "e2e") as hands:
        assert hands.token == "t1"

    assert tool.actions() == ["pose", "stop"]


def test_with_stops_on_an_exception(bench, tool):
    with pytest.raises(RuntimeError, match="boom"), Hands(bench, "e2e"):
        raise RuntimeError("boom")

    assert tool.actions() == ["pose", "stop"]
    assert tool.calls[-1]["controlToken"] == "t1"


def test_a_failed_stop_does_not_hide_the_exception(fake, bench, tool):
    with pytest.raises(RuntimeError, match="boom"), Hands(bench, "e2e"):
        fake.close()
        raise RuntimeError("boom")


def test_a_later_token_replaces_the_kept_one(bench, tool):
    hands = Hands(bench, "e2e")
    hands.start()
    tool.token = "t2"

    hands.rest()

    assert hands.token == "t2"


def test_hold_ms_goes_on_every_pose(bench, tool):
    hands = Hands(bench, "e2e", hold_ms=300000)

    hands.start()
    hands.head("down")
    hands.pose(holdMs=1000)

    assert [call["holdMs"] for call in tool.calls] == [300000, 300000, 1000]


def test_place_sends_a_world_target_for_one_hand(bench, tool):
    answer = Hands(bench, "e2e").place("right", (1, 2.5, 3), pitch=123, yaw=-14, tolerance=0.5, move_ms=0)

    assert tool.calls[-1] == {
        "action": "pose",
        "owner": "e2e",
        "hands": {"right": {"world": [1.0, 2.5, 3.0], "pitch": 123, "yaw": -14}},
        "toleranceUnits": 0.5,
        "moveMs": 0,
    }
    assert answer["corrections"] == 1


def test_place_leaves_out_what_is_not_given(bench, tool):
    Hands(bench, "e2e").place("left", [0, 0, 0])

    assert tool.calls[-1] == {"action": "pose", "owner": "e2e", "hands": {"left": {"world": [0.0, 0.0, 0.0]}}}


def test_place_rejects_a_logical_hand(bench, tool):
    with pytest.raises(ValueError, match="offhand"):
        Hands(bench, "e2e").place("offhand", [0, 0, 0])

    assert tool.calls == []


def test_head_sends_a_preset_or_a_pose(bench, tool):
    hands = Hands(bench, "e2e")

    hands.head("down")
    hands.head({"lookAt": "hands"})

    assert [call["head"] for call in tool.calls] == ["down", {"lookAt": "hands"}]


def test_press_waits_until_the_buttons_are_released(bench, tool, slept):
    Hands(bench, "e2e").press("left", ["grip", "a"], 250)

    assert tool.calls[-1] == {
        "action": "press",
        "owner": "e2e",
        "hand": "left",
        "buttons": ["grip", "a"],
        "durationMs": 250,
    }
    assert slept == [pytest.approx(0.35)]


def test_tap_and_long_press_use_the_framework_thresholds(bench, tool, slept):
    hands = Hands(bench, "e2e")

    hands.tap("right")
    hands.long_press("right", ["b"])

    assert [(call["buttons"], call["durationMs"]) for call in tool.calls] == [
        (["trigger"], devbench.vr.TAP_MS),
        (["b"], devbench.vr.LONG_PRESS_MS),
    ]


def test_a_press_without_a_hold_raises_devbench_error(bench, tool, slept):
    tool.refuse.add("press")

    with pytest.raises(DevbenchError, match="press refused"):
        Hands(bench, "e2e").press("left")

    assert slept == []
