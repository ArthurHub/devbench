"""The pytest plugin: inner pytest sessions against the fake devbench, scripted as a game already in the test cell."""

import pytest
from fake_devbench import FakeFiles

from devbench import Backup
from devbench.testing import Config

MOD_FILE = ("mygames", "Mods_Config/MyMod/MyMod.toml")

CONFTEST = """
import devbench.testing

pytest_plugins = ["devbench.testing"]
DEVBENCH = devbench.testing.Config(
    game="fallout4",
    vr=True,
    tool="mymod",
    actions=["light", "zones"],
    version=lambda: "1.2.3",
    backup=[("mygames", "Mods_Config/MyMod/*")],
    log="MyMod.log",
    areas={AREAS},
    title="My Mod",
)
"""


class FakeGame:
    """
    The fake devbench as Fallout 4 VR with a game loaded in QASmoke, no message box open, the mod's tool (mymod)
    offering actions at version, its config file in the files tool and its log.
    """

    def __init__(self, fake, actions=("light", "zones"), version="1.2.3"):
        self.files = FakeFiles({MOD_FILE: b"original"})
        self.log = ["started"]
        fake.tools["ping"] = lambda args: {"ok": True, "game": "fallout4", "vr": True}
        fake.tools["menu"] = self._menu
        fake.tools["inspect"] = lambda args: {"ok": True, "playerLoaded": True}
        fake.tools["console"] = lambda args: {"ok": True, "compiled": True, "lines": ["GetInCell >> 1.00"]}
        fake.tools["mymod"] = lambda args: {"ok": True, "version": version, "actions": list(actions)}
        fake.tools["files"] = self.files
        fake.tools["log"] = lambda args: {"ok": True, "linesScanned": len(self.log), "lines": list(self.log)}

    def _menu(self, args):
        assert args["action"] == "list"
        return {"ok": True, "openMenus": ["HUDMenu"], "messageBoxOpen": False}


@pytest.fixture
def game(fake):
    return FakeGame(fake)


def _conftest(pytester, areas=None):
    pytester.makeconftest(CONFTEST.replace("{AREAS}", repr(areas or {})))


def _record(reprec):
    """The plugin's record of an inline run."""
    config = reprec.getcall("pytest_configure").config
    return config.pluginmanager.get_plugin("devbench-run").record


def test_config_rejects_an_unknown_game():
    with pytest.raises(ValueError, match="unknown game 'starfield'"):
        Config(game="starfield", vr=False)


def test_config_calls_a_version_callable():
    assert Config(game="fallout4", vr=True, version=lambda: "1.2.3").expected_version() == "1.2.3"
    assert Config(game="fallout4", vr=True).expected_version() is None


def test_a_run_backs_up_the_files_and_puts_them_back(pytester, fake, game):
    _conftest(pytester)
    pytester.makepyfile(
        test_light="""
        from devbench import write_text

        def test_changes_the_config(game, mod, events, log_mark, report):
            write_text(game, "mygames", "Mods_Config/MyMod/MyMod.toml", "changed")
            write_text(game, "mygames", "Mods_Config/MyMod/MyMod.bak", "new")
            assert mod.name == "mymod" and events.prefix == "mymod" and log_mark.start == 1
            report.note("a note from the test")
        """
    )

    reprec = pytester.inline_run("--devbench-port", str(fake.port))

    reprec.assertoutcome(passed=1)
    assert game.files.files == {MOD_FILE: b"original"}
    assert not (pytester.path / ".backup" / "manifest.json").exists()
    record = _record(reprec)
    assert record.notes == [
        "Ran in the game already in QASmoke.",
        "My Mod 1.2.3.",
        "a note from the test",
        "Backed up 1 files, and put them back after: 1 written again, 1 the run made deleted.",
    ]
    assert [(r.nodeid, r.outcome) for r in record.results] == [("test_light.py::test_changes_the_config", "passed")]


def test_a_failed_test_still_puts_the_backup_back(pytester, fake, game):
    _conftest(pytester)
    pytester.makepyfile(
        test_light="""
        from devbench import write_text

        def test_fails(game):
            write_text(game, "mygames", "Mods_Config/MyMod/MyMod.toml", "changed")
            assert False, "broke"
        """
    )

    reprec = pytester.inline_run("--devbench-port", str(fake.port))

    reprec.assertoutcome(failed=1)
    assert game.files.files == {MOD_FILE: b"original"}
    [result] = _record(reprec).results
    assert (result.outcome, result.phase) == ("failed", "call")
    assert "broke" in result.message


def test_a_missing_action_exits_with_its_message(pytester, fake):
    FakeGame(fake, actions=["light"])
    _conftest(pytester)
    pytester.makepyfile(test_light="def test_uses_the_game(game): pass")

    result = pytester.runpytest("--devbench-port", str(fake.port))

    assert result.ret == 2
    result.stdout.fnmatch_lines(["*mymod lacks actions zones: deploy this build*"])
    result.assert_outcomes()


def test_another_build_exits_with_the_versions(pytester, fake):
    FakeGame(fake, version="1.2.2")
    _conftest(pytester)
    pytester.makepyfile(test_light="def test_uses_the_game(game): pass")

    result = pytester.runpytest("--devbench-port", str(fake.port))

    assert result.ret == 2
    result.stdout.fnmatch_lines(["*the game runs mymod 1.2.2, the checkout is 1.2.3: deploy this build*"])


def test_another_game_exits(pytester, fake, game):
    fake.tools["ping"] = lambda args: {"ok": True, "game": "skyrim", "vr": True}
    _conftest(pytester)
    pytester.makepyfile(test_light="def test_uses_the_game(game): pass")

    result = pytester.runpytest("--devbench-port", str(fake.port))

    assert result.ret == 2
    result.stdout.fnmatch_lines(["*is skyrim (VR), expected Fallout 4 VR*"])


def test_a_leftover_backup_is_put_back_before_the_run(pytester, fake, game, bench):
    Backup(bench, [("mygames", "Mods_Config/MyMod/*")], pytester.path / ".backup").take()
    game.files.files[MOD_FILE] = b"left by a crashed run"
    _conftest(pytester)
    pytester.makepyfile(
        test_light="""
        from devbench import read_text

        def test_sees_the_original(game):
            assert read_text(game, "mygames", "Mods_Config/MyMod/MyMod.toml") == "original"
        """
    )

    reprec = pytester.inline_run("--devbench-port", str(fake.port))

    reprec.assertoutcome(passed=1)
    assert _record(reprec).notes[0] == "Put back the backup an earlier run left: 1 files written, 0 deleted."


def test_e2e_restore_puts_the_backup_back_and_runs_no_test(pytester, fake, game, bench):
    Backup(bench, [("mygames", "Mods_Config/MyMod/*")], pytester.path / ".backup").take()
    game.files.files[MOD_FILE] = b"left by a crashed run"
    _conftest(pytester)
    pytester.makepyfile(test_light="def test_never_runs(): assert False")

    result = pytester.runpytest("--devbench-port", str(fake.port), "--e2e-restore")

    assert result.ret == 0
    result.stdout.fnmatch_lines(["*put back the backup: 1 files written, 0 deleted*"])
    result.stdout.no_fnmatch_line("*test_never_runs*")
    assert game.files.files == {MOD_FILE: b"original"}
    assert not (pytester.path / ".backup" / "manifest.json").exists()


def test_e2e_restore_without_a_backup_says_so(pytester, fake):
    _conftest(pytester)

    result = pytester.runpytest("--devbench-port", str(fake.port), "--e2e-restore")

    assert result.ret == 0
    result.stdout.fnmatch_lines(["*no backup is waiting to be put back*"])
    assert fake.calls == []


def test_areas_order_the_tests_without_touching_the_game(pytester, fake):
    _conftest(pytester, areas={"test_c.py": "C", "test_a.py": "A"})
    for name in ("a", "b", "c"):
        pytester.makepyfile(**{f"test_{name}": "def test_one(): pass\ndef test_two(): pass"})

    reprec = pytester.inline_run("--devbench-port", str(fake.port))

    calls = reprec.getcalls("pytest_runtest_logreport")
    order = [call.report.nodeid for call in calls if call.report.when == "call"]
    assert order == [
        "test_c.py::test_one",
        "test_c.py::test_two",
        "test_a.py::test_one",
        "test_a.py::test_two",
        "test_b.py::test_one",
        "test_b.py::test_two",
    ]
    assert [r.area for r in _record(reprec).results][::2] == ["C", "A", "test_b.py"]
    assert fake.calls == []


def test_a_conftest_without_devbench_is_a_usage_error(pytester):
    pytester.makeconftest('pytest_plugins = ["devbench.testing"]')
    pytester.makepyfile(test_light="def test_one(): pass")

    result = pytester.runpytest()

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["*no conftest defines DEVBENCH*"])


def test_mod_and_log_mark_need_their_config_fields(pytester, fake, game):
    pytester.makeconftest(
        """
        import devbench.testing

        pytest_plugins = ["devbench.testing"]
        DEVBENCH = devbench.testing.Config(game="fallout4", vr=True)
        """
    )
    pytester.makepyfile(
        test_light="""
        def test_mod(mod): pass
        def test_log_mark(log_mark): pass
        def test_events(events): assert events.prefix is None
        """
    )

    result = pytester.runpytest("--devbench-port", str(fake.port))

    result.assert_outcomes(passed=1, errors=2)
    result.stdout.fnmatch_lines(["*the mod fixture needs Config.tool*", "*the log_mark fixture needs Config.log*"])


def test_a_mod_wraps_the_game_fixture(pytester, fake, game):
    pytester.makeconftest(
        CONFTEST.replace("{AREAS}", "{}")
        + """
import pytest
from devbench import write_text

@pytest.fixture(scope="session")
def game(game, report):
    report.note("mod setup")
    yield game
    write_text(game, "mygames", "Mods_Config/MyMod/MyMod.toml", "teardown before the restore")
    report.note("mod teardown")
"""
    )
    pytester.makepyfile(test_light="def test_one(game): pass")

    reprec = pytester.inline_run("--devbench-port", str(fake.port))

    reprec.assertoutcome(passed=1)
    assert game.files.files == {MOD_FILE: b"original"}
    notes = _record(reprec).notes
    assert notes.index("mod setup") < notes.index("mod teardown") < len(notes) - 1
