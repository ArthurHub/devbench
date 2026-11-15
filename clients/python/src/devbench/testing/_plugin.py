"""The pytest hooks and fixtures of devbench.testing: the run's setup and teardown around a mod's suite."""

from __future__ import annotations

import types
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

import pytest

from devbench.checks import RequirementError, require, require_actions, require_tools, require_version
from devbench.client import Devbench, DevbenchError, ModTool, find_port
from devbench.events import Events
from devbench.files import Backup
from devbench.games import fallout4
from devbench.log import LogMark
from devbench.testing._config import Config
from devbench.testing._record import Record

# what setup failures exit the session with
_EXIT_CODE = 2

# the game setup of each game: enter a game the tests can run in, and say what was done
_ENTER: dict[str, Callable[[Devbench, str], fallout4.Entered]] = {
    "fallout4": lambda bench, cell: fallout4.enter_game(bench, cell),
}


@dataclass
class _Run:
    """
    The session's state, kept on pytest's config: the mod's Config, the folder of the conftest that defines it, the
    run's record and the log mark the game fixture took. Registered as a plugin, it records each test's result.
    """

    config: Config
    home: Path
    record: Record
    mark: LogMark | None = None

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


_RUN = pytest.StashKey[_Run]()


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
    run = _Run(devbench, home, Record(areas=devbench.areas))
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
        yield bench
    finally:
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


@pytest.fixture(scope="session")
def report(pytestconfig: pytest.Config) -> Record:
    """The run's record, which a test adds notes to."""
    return _run(pytestconfig).record
