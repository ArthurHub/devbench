"""The pytest hooks and fixtures of devbench.testing: the run's setup and teardown around a mod's suite."""

from __future__ import annotations

import types
from collections.abc import Callable, Generator, Iterator
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any, NoReturn

import pytest

from devbench.checks import RequirementError, require, require_actions, require_tools, require_version
from devbench.client import Devbench, DevbenchError, ModTool, find_port
from devbench.events import Events
from devbench.files import Backup, delete_file, read_bytes
from devbench.games import fallout4
from devbench.log import LogMark
from devbench.testing._config import Config
from devbench.testing._picture import bmp_to_png
from devbench.testing._record import Failure, Record
from devbench.testing.report import write

# what setup failures exit the session with
_EXIT_CODE = 2

# the log lines since the test started that a failure keeps
_LOG_TAIL = 100

# the longest side of a failure's dump, in pixels: a third of FO4VR's 6144-wide frame, so each eye is 1024 wide
_PICTURE_SIZE = 2048

# the game setup of each game: enter a game the tests can run in, and say what was done
_ENTER: dict[str, Callable[[Devbench, str], fallout4.Entered]] = {
    "fallout4": lambda bench, cell: fallout4.enter_game(bench, cell),
}


@dataclass
class _Run:
    """
    The session's state, kept on pytest's config: the mod's Config, the folder of the conftest that defines it, the
    run's record, the log mark the game fixture took, the game while that fixture is up, and the current test's log
    mark. Registered as a plugin, it records each test's result and what a failed test leaves.
    """

    config: Config
    home: Path
    record: Record
    mark: LogMark | None = None
    game: Devbench | None = None
    test_mark: tuple[str, LogMark] | None = None
    # set by the first failure picture that could not be taken: no later failure tries again
    pictures_off: bool = field(default=False)
    # the crashes of the setup failures captured so far: a session fixture's error fails every later test's setup
    # again, and only its first test takes the picture and log tail
    setup_crashes: set[tuple[str, int, str]] = field(default_factory=set)

    def backup(self, bench: Devbench) -> Backup | None:
        """The backup of Config.backup in <home>/.backup, or None when the config backs nothing up."""
        return Backup(bench, list(self.config.backup), self.home / ".backup") if self.config.backup else None

    def backup_pending(self) -> bool:
        """
        Whether a backup a run left waits in <home>/.backup, checked without a connection to the game: the manifest
        Backup writes is there.
        """
        return bool(self.config.backup) and (self.home / ".backup" / "manifest.json").is_file()

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        self.record.add(report)

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_makereport(
        self, item: pytest.Item, call: pytest.CallInfo[None]
    ) -> Generator[None, pytest.TestReport, pytest.TestReport]:
        """
        On the first failed phase of a test that uses the game fixture, while the game is up: take its failure
        picture and log tail, before its teardown changes what the game shows. A setup failure with the crash of one
        already captured (a failed session fixture, raised again for each test) takes nothing.
        """
        report = yield
        failures = self.record.failures
        if report.failed and self.game is not None and "game" in item.fixturenames and item.nodeid not in failures:
            if not self._repeated_setup_crash(report):
                failures[item.nodeid] = self._capture(self.game, item.nodeid)
        return report

    def _repeated_setup_crash(self, report: pytest.TestReport) -> bool:
        """Whether a failed report is a setup failure whose crash (file, line, message) an earlier setup failure had."""
        crash = getattr(report.longrepr, "reprcrash", None)
        if report.when != "setup" or crash is None:
            return False
        key = (str(crash.path), crash.lineno, crash.message)
        if key in self.setup_crashes:
            return True
        self.setup_crashes.add(key)
        return False

    def _capture(self, game: Devbench, nodeid: str) -> Failure:
        """
        What a failed test leaves: the log lines since it started (when Config.log is set) and a picture of
        Config.picture. The first picture that cannot be taken says why in its row and a note, and turns pictures off.
        """
        failure = Failure()
        if self.test_mark is not None and self.test_mark[0] == nodeid:
            try:
                failure.log = self.test_mark[1].lines()[-_LOG_TAIL:]
            except (DevbenchError, OSError) as error:
                failure.log = [f"the log could not be read: {error}"]
        if self.config.picture is not None and not self.pictures_off:
            try:
                failure.picture = self._picture(game, nodeid)
            except (DevbenchError, OSError, KeyError, ValueError) as error:
                failure.picture_error = str(error)
                self.pictures_off = True
                self.record.note(f"No failure pictures from {nodeid} on: {error}")
        return failure

    def _picture(self, game: Devbench, nodeid: str) -> str:
        """
        Dump Config.picture, delete the game's copy and save it in the report's pictures folder as a PNG (in VR, only
        the left eye); returns its path in the report folder. The dump lands under the game's Data folder, which the
        files tool reads as "data".
        """
        answer = game.tool("rendertarget", action="dump", index=self.config.picture, maxDimension=_PICTURE_SIZE)
        path = _data_path(answer["file"])
        data = read_bytes(game, "data", path)
        if data is None:
            raise DevbenchError(f"the dump {path} is not in the Data folder the files tool sees")
        delete_file(game, "data", path)
        local = self.record.reserve(nodeid, ".png")
        local.write_bytes(bmp_to_png(data, left_half=self.config.vr))
        return local.relative_to(self.record.folder).as_posix()


_RUN = pytest.StashKey[_Run]()


def _data_path(file: str) -> str:
    """
    A file's path under the game's Data folder, '/' separated, from its absolute path: what follows the last folder
    named Data. ValueError when no folder is.
    """
    parts = PureWindowsPath(file).parts
    data = [i for i, part in enumerate(parts) if part.lower() == "data"]
    if not data:
        raise ValueError(f"the dump {file} is not under the game's Data folder")
    return "/".join(parts[data[-1] + 1 :])


def _report_root(devbench: Config, home: Path) -> Path:
    """
    The folder the report's run folders go in: Config.report_dir (relative: to home), or build/e2e under the first
    folder from home up that holds a .git, or under home when none does.
    """
    if devbench.report_dir is not None:
        return home / devbench.report_dir
    repo = next((folder for folder in (home, *home.parents) if (folder / ".git").exists()), home)
    return repo / "build" / "e2e"


def _find_config(config: pytest.Config) -> tuple[Config, Path]:
    """
    The DEVBENCH object of the one registered module (the rootdir conftest) that defines it, and that module's folder.
    None, several, or one that is not a Config raises pytest.UsageError.
    """
    found = {
        id(plugin): plugin
        for plugin in config.pluginmanager.get_plugins()
        if isinstance(plugin, types.ModuleType) and hasattr(plugin, "DEVBENCH")
    }
    modules = list(found.values())
    if not modules:
        raise pytest.UsageError(
            "devbench.testing: no conftest defines DEVBENCH = devbench.testing.Config(...): define it in the rootdir "
            "conftest, beside pytest_plugins"
        )
    if len(modules) > 1:
        names = ", ".join(str(getattr(module, "__file__", module.__name__)) for module in modules)
        raise pytest.UsageError(f"devbench.testing: DEVBENCH is defined in more than one conftest: {names}")
    module = modules[0]
    devbench = module.DEVBENCH
    if not isinstance(devbench, Config):
        raise pytest.UsageError(
            f"devbench.testing: DEVBENCH in {module.__file__} is a {type(devbench).__name__}, not a "
            "devbench.testing.Config"
        )
    return devbench, Path(module.__file__).resolve().parent


def _run(config: pytest.Config) -> _Run:
    return config.stash[_RUN]


def _exit(message: str) -> NoReturn:
    pytest.exit(message, returncode=_EXIT_CODE)


def _connect(config: pytest.Config) -> Devbench:
    """A client on --devbench-port or the port the game's runtime.json names, checked to be the Config's game."""
    devbench = _run(config).config
    port = config.getoption("--devbench-port") or find_port(devbench.game, devbench.vr)
    bench = Devbench(port)
    try:
        require(bench, devbench.game, devbench.vr)
    except RequirementError as error:
        bench.close()
        _exit(str(error))
    return bench


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("devbench")
    group.addoption("--devbench-port", type=int, help="devbench's port; by default the one its runtime.json has")
    group.addoption(
        "--e2e-restore", action="store_true", help="put back the files of a backup a run left, and run no test"
    )


def pytest_configure(config: pytest.Config) -> None:
    devbench, home = _find_config(config)
    record = Record(areas=devbench.areas, title=devbench.title or devbench.tool or devbench.game)
    record.directory = _report_root(devbench, home) / record.started.strftime("%Y%m%d-%H%M%S")
    run = _Run(devbench, home, record)
    config.stash[_RUN] = run
    config.pluginmanager.register(run, "devbench-run")


def pytest_sessionstart(session: pytest.Session) -> None:
    """With --e2e-restore: put back a backup a run left and exit, before any test is collected."""
    config = session.config
    if not config.getoption("--e2e-restore"):
        return
    run = _run(config)
    if not run.backup_pending():
        pytest.exit("no backup is waiting to be put back", returncode=0)
    bench = _connect(config)
    try:
        backup = run.backup(bench)
        assert backup is not None  # backup_pending holds only with Config.backup set
        written, deleted = backup.restore()
    finally:
        bench.close()
    pytest.exit(f"put back the backup: {len(written)} files written, {len(deleted)} deleted", returncode=0)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Run the tests in the order of Config.areas (by test-file name); files it does not list run last."""
    order = list(_run(config).config.areas)
    if order:
        items.sort(key=lambda item: order.index(item.path.name) if item.path.name in order else len(order))


@pytest.fixture(scope="session")
def bench(pytestconfig: pytest.Config) -> Iterator[Devbench]:
    """The running game's devbench, checked to be the Config's game (and VR); anything else exits the run."""
    bench = _connect(pytestconfig)
    yield bench
    bench.close()


def _setup_step(what: str, step: Callable[[], Any]) -> Any:
    """Run one step of the game's setup; a failure exits the run with what failed and why."""
    try:
        return step()
    except RequirementError as error:
        _exit(str(error))
    except (DevbenchError, TimeoutError, OSError) as error:
        _exit(f"{what}: {error}")


def _check_mod(bench: Devbench, devbench: Config, run: _Run) -> None:
    """The mod's tool is listed, offers the Config's actions and reports the checkout's version."""
    assert devbench.tool is not None
    mod = ModTool(bench, devbench.tool)
    require_tools(bench, [devbench.tool])
    health = require_actions(mod, devbench.actions)
    expected = devbench.expected_version()
    if expected is not None:
        health = require_version(mod, expected)
    if "version" in health:
        run.record.note(f"{devbench.title or devbench.tool} {health['version']}.")


@pytest.fixture(scope="session")
def game(bench: Devbench, pytestconfig: pytest.Config) -> Iterator[Devbench]:
    """
    The game the tests run in: a leftover backup put back, the game entered in Config.cell and settled, the mod
    checked, the files of Config.backup backed up and the log mark set. The backup is put back at the end, also when
    the session fails; a crash leaves it for the next run or --e2e-restore.
    """
    run = _run(pytestconfig)
    devbench = run.config
    record = run.record
    backup = run.backup(bench)
    if backup is not None and backup.pending():
        written, deleted = _setup_step("putting back the backup an earlier run left", backup.restore)
        record.note(f"Put back the backup an earlier run left: {len(written)} files written, {len(deleted)} deleted.")

    enter = _ENTER.get(devbench.game)
    if enter is None:
        _exit(f"devbench.testing has no game setup for {devbench.game}")
    entered = _setup_step(f"entering the game in {devbench.cell}", lambda: enter(bench, devbench.cell))
    record.dialogs.extend(entered.dialogs)
    if entered.started:
        record.note(f"Started a new game in {devbench.cell} from the main menu.")
    else:
        record.note(f"Ran in the game already in {devbench.cell}.")
    if entered.quiet is False:
        record.note("The game still popped up dialogs at the settle limit: the tests started anyway.")

    if devbench.tool is not None:
        _setup_step(f"checking {devbench.tool}", lambda: _check_mod(bench, devbench, run))

    files = _setup_step("taking the backup", backup.take) if backup is not None else 0
    try:
        if devbench.log is not None:
            log = devbench.log
            run.mark = _setup_step(f"marking {log}", lambda: LogMark(bench, log))
        run.game = bench
        yield bench
    finally:
        run.game = None
        if backup is not None:
            try:
                written, deleted = backup.restore()
            except Exception as error:
                raise RuntimeError(
                    f"the backup was not put back: {error}: run pytest --e2e-restore once the game answers"
                ) from error
            record.note(
                f"Backed up {files} files, and put them back after: {len(written)} written again, "
                f"{len(deleted)} the run made deleted."
            )


@pytest.fixture(scope="session")
def mod(game: Devbench, pytestconfig: pytest.Config) -> ModTool:
    """The mod's own devbench tool (Config.tool), checked by the game fixture."""
    tool = _run(pytestconfig).config.tool
    if tool is None:
        pytest.fail("the mod fixture needs Config.tool", pytrace=False)
    return ModTool(game, tool)


@pytest.fixture
def events(game: Devbench, pytestconfig: pytest.Config) -> Events:
    """The events published from the start of the test; with Config.tool, the mod's topics match unprefixed."""
    return Events(game, prefix=_run(pytestconfig).config.tool)


@pytest.fixture(scope="session")
def log_mark(game: Devbench, pytestconfig: pytest.Config) -> LogMark:
    """The mark in Config.log the game fixture set, just before the first test."""
    mark = _run(pytestconfig).mark
    if mark is None:
        pytest.fail("the log_mark fixture needs Config.log", pytrace=False)
    return mark


@pytest.fixture(autouse=True)
def devbench_test_mark(request: pytest.FixtureRequest) -> None:
    """
    For a test that uses the game fixture, with Config.log set: a mark in the log as the test starts, which a failure's
    log tail reads from. A mark that cannot be taken leaves the failure without a tail.
    """
    run = _run(request.config)
    run.test_mark = None
    log = run.config.log
    if log is None or "game" not in request.fixturenames:
        return
    game = request.getfixturevalue("game")
    try:
        run.test_mark = (request.node.nodeid, LogMark(game, log))
    except (DevbenchError, OSError):
        pass


# named so the package's report attribute stays the devbench.testing.report module
@pytest.fixture(scope="session", name="report")
def report_fixture(pytestconfig: pytest.Config) -> Record:
    """The run's record, which a test adds notes, sections and pictures to."""
    return _run(pytestconfig).record


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter, config: pytest.Config) -> None:
    """Write the report and print its link, unless the run collected only, restored, or has no result."""
    run = config.stash.get(_RUN, None)
    if run is None or config.getoption("collectonly") or config.getoption("--e2e-restore") or not run.record.results:
        return
    terminalreporter.write_line(f"Report: {write(run.record).as_uri()}", bold=True)
