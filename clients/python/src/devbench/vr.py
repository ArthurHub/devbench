"""VR hands through devbench's input tool: a held pose of the HMD and both controllers, hands placed at world points,
presses on top of the hold. The game's input handling sees all of it as the real devices.

Hands are the physical controllers (left / right); mapping a mod's logical hand (primary / offhand) stays in the mod.
"""

from __future__ import annotations

import http.client
import time
from collections.abc import Sequence
from typing import Any

from devbench.client import Devbench, DevbenchError

# F4VR-CommonFramework's gesture thresholds, not devbench's: a tap is released within 0.3 s, a long press held over
# 0.6 s
TAP_MS = 100
LONG_PRESS_MS = 1000

# extra wait after a press's duration so its release has reached the game when press returns
_RELEASE_MARGIN = 0.1

_HANDS = ("left", "right")


class Hands:
    """
    devbench's held pose as one owner: start() takes over the HMD and both controllers, stop() hands them back.
    A context manager that starts on entry and always stops on exit, so a failure never leaves the headset held.
    hold_ms (devbench's 60 s when None) goes on every pose; a hold that runs out makes the next press answer 409.
    """

    def __init__(self, bench: Devbench, owner: str, *, hold_ms: int | None = None) -> None:
        self.bench = bench
        self.owner = owner
        self.hold_ms = hold_ms
        self.token: str | None = None

    def __enter__(self) -> Hands:
        self.start()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *exc_info: object) -> None:
        if exc_type is None:
            self.stop()
            return
        try:
            self.stop()
        except (OSError, http.client.HTTPException):
            pass  # the exception already unwinding is the failure to report

    def ready(self) -> bool:
        """
        Whether devbench can drive the VR devices now (the vrTrackedSet capability: OpenVR found, hooks in place).
        A refused or missing input tool raises DevbenchError.
        """
        answer = self.bench.tool("input", action="capabilities")
        tracked = answer.get("capabilities", {}).get("vrTrackedSet", {})
        return bool(tracked.get("available") and tracked.get("ready"))

    def start(self) -> dict[str, Any]:
        """
        Take over the HMD and both controllers in devbench's ready pose and return its answer. It names the ready
        pose, so a hold this owner left behind (a crashed run) moves back to it too.
        """
        return self.pose(hands="ready", head="ready")

    def rest(self) -> dict[str, Any]:
        """Both hands and the head back in devbench's ready pose; returns devbench's answer."""
        return self.pose(hands="ready", head="ready")

    def stop(self) -> None:
        """
        Hand the devices back to the physical ones. Without a token it does nothing; a refused stop (the hold ran out,
        or another sequence took the devices) is ignored. The token is cleared either way.
        """
        if self.token is None:
            return
        token, self.token = self.token, None
        try:
            self.bench.tool("input", action="stop", owner=self.owner, controlToken=token)
        except DevbenchError:
            pass

    def pose(self, **args: Any) -> dict[str, Any]:
        """
        One input pose call as this owner with the tool's own arguments (hands, head, holdMs, ...), keeping its
        control token for stop. hold_ms fills holdMs when args leave it out. Returns devbench's answer.
        """
        if self.hold_ms is not None:
            args.setdefault("holdMs", self.hold_ms)
        answer = self.bench.tool("input", action="pose", owner=self.owner, **args)
        self.token = answer.get("controlToken") or self.token
        return answer

    def place(
        self,
        hand: str,
        world: Sequence[float],
        *,
        pitch: float | None = None,
        yaw: float | None = None,
        corrections: int | None = None,
        tolerance: float | None = None,
        move_ms: int | None = None,
    ) -> dict[str, Any]:
        """
        Move a physical hand's wand (left / right) to a world point; the other hand stays. pitch / yaw (degrees) point
        the controller, passed as devbench takes them; corrections, tolerance (world units) and move_ms tune the move.
        Returns devbench's answer: corrections made, and per hand where the wand landed and its error.
        """
        if hand not in _HANDS:
            raise ValueError(f"hand must be 'left' or 'right', not {hand!r}")
        target: dict[str, Any] = {"world": [float(c) for c in world]}
        if pitch is not None:
            target["pitch"] = pitch
        if yaw is not None:
            target["yaw"] = yaw
        options = {"corrections": corrections, "toleranceUnits": tolerance, "moveMs": move_ms}
        return self.pose(hands={hand: target}, **{key: value for key, value in options.items() if value is not None})

    def head(self, preset_or_pose: str | dict[str, Any]) -> dict[str, Any]:
        """
        Turn the head: a preset ("ready", "down") or {pitch?, yaw?, lookAt?, ...} as the input tool takes it.
        Returns devbench's answer.
        """
        return self.pose(head=preset_or_pose)

    def press(self, hand: str, buttons: Sequence[str] = ("trigger",), duration_ms: int = TAP_MS) -> None:
        """
        Hold buttons (trigger, grip, a, b, thumbstick) on a physical controller for duration_ms on top of the hold,
        and return once they are released. Without a hold of this owner devbench answers 409 (DevbenchError).
        """
        self.bench.tool(
            "input", action="press", owner=self.owner, hand=hand, buttons=list(buttons), durationMs=duration_ms
        )
        time.sleep(duration_ms / 1000 + _RELEASE_MARGIN)

    def tap(self, hand: str, buttons: Sequence[str] = ("trigger",)) -> None:
        """A press short enough to count as a tap (TAP_MS)."""
        self.press(hand, buttons, TAP_MS)

    def long_press(self, hand: str, buttons: Sequence[str] = ("trigger",)) -> None:
        """A press long enough to count as a long press (LONG_PRESS_MS)."""
        self.press(hand, buttons, LONG_PRESS_MS)
