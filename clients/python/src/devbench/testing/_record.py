"""The record of a run: its notes, the dialogs it closed and each test's result, which the report renders."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import PurePosixPath

import pytest

# the end of a failure's text kept when pytest gives no one-line crash message
_FAILURE_TAIL = 3000


@dataclass
class Result:
    """
    One test's result: the call's outcome, or "error" / "skipped" when its setup or teardown failed or skipped (phase
    says which). area is the area its file belongs to, or the file name when Config.areas does not list it.
    """

    nodeid: str
    file: str
    name: str
    area: str
    outcome: str
    phase: str
    duration: float
    message: str


@dataclass
class Record:
    """What a run found, as the plugin and the tests add it: notes, the dialogs closed, and the results in run order."""

    areas: Mapping[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    dialogs: list[str] = field(default_factory=list)
    results: list[Result] = field(default_factory=list)

    def note(self, text: str) -> None:
        """Add a line about the run as a whole."""
        self.notes.append(text)

    def add(self, report: pytest.TestReport) -> None:
        """
        Fold one of pytest's phase reports into its test's result. A passed setup or teardown adds nothing; a later
        phase that did not pass overrides a passed call (a failed teardown makes the test an error), and the first
        failure's message is kept.
        """
        if report.when != "call" and report.passed:
            return
        outcome = report.outcome if report.when == "call" else ("error" if report.failed else report.outcome)
        message = ""
        if report.failed:
            crash = getattr(report.longrepr, "reprcrash", None)
            message = crash.message if crash else str(report.longrepr)[-_FAILURE_TAIL:]
        elif report.skipped and isinstance(report.longrepr, tuple):
            message = report.longrepr[2]
        result = next((result for result in self.results if result.nodeid == report.nodeid), None)
        if result:
            if outcome != "passed":
                result.outcome, result.phase = outcome, report.when
                result.message = result.message or message
            return
        path, _, name = report.nodeid.partition("::")
        file = PurePosixPath(path).name
        self.results.append(
            Result(
                report.nodeid,
                file,
                name,
                self.areas.get(file, file),
                outcome,
                report.when,
                report.duration,
                message,
            )
        )
