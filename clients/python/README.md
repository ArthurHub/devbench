# devbench-client

Python client for devbench's REST port: call a running game's tools from a script, a REPL or a test. Import package
`devbench`; it never imports pytest. MIT licensed (see [LICENSE](LICENSE)), unlike the GPL plugin.

## Install

From a git tag, in a mod's `requirements.txt` (pick the remote and the tag):

```
devbench-client @ git+https://github.com/ArthurHub/devbench@v1.15.0#subdirectory=clients/python
```

From a local checkout, editable, when working on devbench and a mod together:

```
pip install -e <devbench>/clients/python
```

## Use

```python
from devbench import Devbench, ModTool, find_port

with Devbench(find_port("fallout4", vr=True)) as bench:
    print(bench.health())
    print(bench.tool("console", command="GetInCell QASmoke"))
    print(ModTool(bench, "immersiveflashlightvr").health())
```

Check that the running game is the one a run needs before using it. Each check raises `RequirementError` with a
message that says what was found and what to do ("deploy this build"):

```python
from devbench import require, require_actions, require_tools, require_version

require(bench, "fallout4", vr=True)  # the ping answer; no answer or another game raises
require_tools(bench, ["frik"])  # from devbench's tool listing (bench.tools())
mod = ModTool(bench, "immersiveflashlightvr")
require_actions(mod, ["gesture", "zones", "light"])  # from the mod tool's health
require_version(mod, "1.4.2")  # exact match with the health's version; returns the health
```

Read what an action caused from devbench's events. `Events` sees only events published after it was made; with a
prefix (a mod's tool name) a topic also matches as `<prefix>.<topic>`:

```python
from devbench import Events

mod = ModTool(bench, "immersiveflashlightvr")
events = Events(bench, prefix=mod.prefix)
mod.call("gesture", gesture="toggle")
event = events.wait("gesture", timeout=3.0, where=lambda data: data["gesture"] == "toggle")
print(len(events.all("gesture")), event["seq"])
```

`wait` raises `TimeoutError` naming the topic and the topics that arrived. A read raises `DevbenchError` when events
were lost (more than the 256-event ring between two reads) or the game restarted.

Run console commands and handle menus with free functions that take the client:

```python
from devbench import close_dialogs, close_menus, console, console_number, open_menus

console(bench, "player.GetPos z")  # the lines it printed
console_number(bench, "player.GetInCell QASmoke")  # 1.0: the number after its '>>'
"HUDMenu" in open_menus(bench)
said = close_dialogs(bench)  # answer each message box with its first button
close_menus(bench, ["PauseMenu"])  # a refused close is ignored
```

A command that does not compile raises `DevbenchError`, and so does `console_number` when the output holds no number.
`close_dialogs` returns what each box said and gives up after `limit` (20) answers.

Read and write files as the game sees them, through devbench's `files` tool. `root` is `"data"` (the Data folder,
mod manager's virtual files included) or `"mygames"` (Documents/My Games/<game>):

```python
from devbench import Backup, delete_file, list_files, read_bytes, read_text, write_bytes, write_text

[f["path"] for f in list_files(bench, "data", "MCM/Settings/*.ini")]  # glob: '*', '?', '**'; case ignored
read_text(bench, "data", "MCM/Settings/MyMod.ini")  # None when there is no file; UTF-8, else cp1252
write_text(bench, "mygames", "Mods_Config/MyMod/MyMod.toml", "key = 1\n")
read_bytes(bench, "data", "x.bin"), write_bytes(bench, "data", "x.bin", b"\x01"), delete_file(bench, "data", "x.bin")
```

A listing that is not whole (the walk failed partway, or more than 10000 files) raises `DevbenchError`.

`Backup` saves the files of some globs before a run changes them and puts them back after:

```python
backup = Backup(bench, [("mygames", "Mods_Config/MyMod/*")], "tests/e2e/.backup")
if backup.pending():  # a run that a crash ended
    backup.restore()
backup.take()  # the number of files saved
...
written, deleted = backup.restore()  # "root/path" lists
```

The manifest (`<folder>/manifest.json`) is written whole before `take` returns, so it survives a crash. `restore`
writes back each file that differs, deletes each file the globs list that the manifest lacks (case ignored), then
removes the manifest. `take` raises while a backup is pending; `restore` raises when none is.

Read what a plugin logged after a point, from its log in the extender's log folder:

```python
mark = LogMark(bench, "MyMod.log")  # the line count now; a missing file raises DevbenchError
...
mark.lines()  # the lines written since the mark
mark.errors()  # those that are error or critical lines; errors(pattern=r"^\S+ warn") for others
```

`errors` matches the mods' `<time> error <msg>` format and devbench's own `[<time>] [E] <msg>`; `pattern` is a regex
string or compiled pattern, found with `re.search`. A log shorter than the mark was restarted with the game, and all of
it counts as new. The log tool returns at most the last 5000 lines, so more than that returns the last 5000 and
`mark.missed` says how many were not read.

Drive the VR hands (Fallout 4 VR) through devbench's `input` pose: it holds the HMD and both controllers, places a
hand's wand at a world point and presses buttons on top, and the game sees real devices:

```python
from devbench import Hands

hands = Hands(bench, "mymod-e2e")  # the owner of the hold; hold_ms= for a hold longer than devbench's 60 s
if hands.ready():  # the vrTrackedSet capability: OpenVR found, hooks in place
    with hands:  # starts in the ready pose; always stops, handing the devices back
        answer = hands.place("left", [x, y, z], pitch=10, yaw=10)  # devbench's answer: corrections, hands
        hands.place("offhand", center, head_offset=(5, 0, -3), yaw_in=25)  # mirrors for either hand
        hands.head("down")  # "ready", "down" or {pitch?, yaw?, lookAt?, ...}
        hands.tap("left")  # press("left", ["trigger"], 100); returns once released
        hands.long_press("right", ["grip"])  # 1000 ms
        hands.rest()  # hands and head back in the ready pose
        hands.pose(hands={"right": {"node": "LArm_Hand", "front": 10}})  # any other pose arguments
```

A hand is a physical controller (`left` / `right`) or a role (`primary` / `offhand`), which devbench resolves against
the game's handedness when the call arrives; any other name raises `ValueError`. `pitch` and `yaw` pass through as the
`input` tool takes them. `head_offset` (outward, forward, up) moves the point along the head's axes as posed, outward
toward the hand's own side, and `yaw_in` replaces `yaw` with a turn toward the body (in tracking space, mirrored around
the body's forward), so one recorded placement fits either hand and either handedness. `TAP_MS` (100) and `LONG_PRESS_MS` (1000) are F4VR-CommonFramework's gesture thresholds.
A press without a hold of this owner (it never started, or the hold ran out) raises `DevbenchError` (409). `stop`
ignores a refused stop, and on an exception inside the `with` it never hides that exception.

Read and set the game's handedness (`bLeftHandedMode:VR` on Fallout 4 VR):

```python
from devbench.vr import left_handed, set_left_handed

was = set_left_handed(bench, True)  # the value before; answers once the game's wands have swapped
assert left_handed(bench)
set_left_handed(bench, was, owner="mymod-e2e")  # under that owner's pose hold, when it runs one
```

devbench checks the swap under the pose hold of `owner` when it runs one, else under a short hold of its own. Another
sequence holding the devices (409) or a game that did not follow (504, the old value put back) raise `DevbenchError`.

Put Fallout 4 (or VR) in a test cell, so nothing a run does reaches a save:

```python
from devbench.games import fallout4

entered = fallout4.enter_game(bench)  # cell="QASmoke"; Entered(started, dialogs, quiet)
fallout4.in_cell(bench, "QASmoke")  # False at the main menu
fallout4.settle(bench, quiet=10, limit=120)  # Settled(dialogs, quiet)
```

From the main menu `enter_game` runs `coc <cell>`, waits up to `timeout` (300 s) for the HUD with no main menu or
loading screen, then settles: it waits until no message box has popped up for `quiet` seconds, answering each with its
first button, and gives up after `limit` seconds with `quiet` False. A game already in the cell is reused
(`started` False, `quiet` None); a game in another cell, or a load in progress, raises `RequirementError`. A `coc`
that a modal blocked raises `DevbenchError`. The cell is an interior cell's editor ID; an unknown one raises
`DevbenchError`. Nothing is printed: `dialogs` holds what each closed box said.

## pytest plugin

`devbench.testing` runs a mod's end-to-end suite in the game: it connects, enters a game in the test cell, checks the
mod, backs up the files a run changes and puts them back after. It is opt-in (no entry point), so it never loads into
an unrelated pytest run. The mod's **rootdir** conftest (the one beside its `pytest.ini`; pytest honors
`pytest_plugins` nowhere else) turns it on and configures it:

```python
import devbench.testing

pytest_plugins = ["devbench.testing"]
DEVBENCH = devbench.testing.Config(
    game="fallout4",
    vr=True,
    tool="immersiveflashlightvr",  # the mod's devbench tool; None skips the mod check
    actions=["gesture", "zones", "light"],  # the actions the tests call
    version=lambda: read_checkout_version(),  # a string or a callable; None skips the version check
    backup=[("mygames", "Mods_Config/ImmersiveFlashlightVR/*")],  # (root, glob) pairs; none: no backup
    log="ImmersiveFlashlightVR.log",  # for the log_mark fixture
    areas={"test_light.py": "Light action", "test_health.py": "Health"},  # run order, by test-file name
    title="Immersive Flashlight VR",
    cell="QASmoke",  # the interior cell the game runs in
    picture=6,  # the render target dumped when a test fails (FO4VR: 6, the lit frame); None: no picture
    report_dir=None,  # where the report's run folders go; None: build/e2e under the repo root
    handedness="right",  # VR: "left" / "right" for the run, the player's put back after; None: leave it
)
```

Fixtures:

| Fixture                 | Gives                                                                                                       |
| ----------------------- | ----------------------------------------------------------------------------------------------------------- |
| `bench` (session)       | the `Devbench`, checked to be the configured game and VR; connects only when a test needs it                |
| `game` (session)        | the `Devbench`, once the game is set up (below); the backup is put back at the end, also when the run fails |
| `mod` (session)         | `ModTool` of `tool`                                                                                         |
| `events`                | `Events` from the start of the test, with the mod's tool as prefix                                          |
| `log_mark` (session)    | the `LogMark` in `log`, set just before the first test                                                      |
| `left_handed` (session) | whether the run is left-handed: what `game` set, else the game's own                                        |
| `report` (session)      | the run's record, which the HTML report renders (below)                                                     |

`game` puts back a backup a crashed run left, runs `enter_game(cell)`, checks the mod (`require_tools`, then
`require_actions`, then `require_version`), puts back a handedness a crashed run left, takes the backup into `.backup/`
beside the conftest, sets the run's handedness, and sets the log mark.
A setup failure (another game, a missing action, another build, a game outside the cell) exits the run with code 2 and
the message that says what to do.

Tests run in `areas` order; files it does not list run last. `--devbench-port` picks the port (default: the game's
`runtime.json`). `--e2e-restore` puts back a backup a run left and runs no test; a restore that fails at the end of a
run keeps the backup for it.

With `handedness` (or `--left-handed`, which overrides it) `game` writes the player's handedness to
`.backup/handedness.json`, sets the run's with `set_left_handed` (devbench answers once the game's wands have swapped)
and notes "Ran left-handed." / "Ran right-handed." in the report. At the end it puts the player's back, before the
files, also when the run fails, and deletes the file. A file a crashed run left is put back at the next run's start or
by `--e2e-restore`; one `--e2e-restore` cannot set (no loaded game) is kept, and it exits with code 2.

A mod's own session setup wraps `game`: a fixture of the same name in its conftest requests the plugin's. Its setup runs
after the backup, the handedness and the log mark (so it can wait for its mod to follow the handedness), its teardown
before the handedness and the backup are put back:

```python
@pytest.fixture(scope="session")
def game(game, left_handed, report):
    wait_until(lambda: MyMod(game).left_handed() == left_handed, 5, what="the mod following the handedness")
    yield game
    MyMod(game).clear()
```

### Report

At the end of a run the plugin writes one HTML page and prints its link: `build/e2e/<YYYYmmdd-HHMMSS>/index.html`
under the first folder up from the `DEVBENCH` conftest that holds a `.git` (`report_dir` overrides
`<repo>/build/e2e`; relative to the conftest's folder). It shows the totals, the notes, the failures, each test's
result by area in `areas` order, the mod's sections, the game dialogs the run closed and a gallery of the mod's
pictures. Nothing is written for `--collect-only`, `--e2e-restore` or a run without results.

When a test that uses `game` fails, the failure row gets:

- the lines `log` gained since the test started (the last 100, collapsed);
- a picture of render target `picture` (`rendertarget dump` at 2048, the game's copy deleted, saved beside the page as
  PNG; in VR only the left eye, 1024x1088 on FO4VR). The first picture that can't be taken (a 501 off the main thread,
  a wrong index) says why in its row and in a note, and no later failure tries again.

A test adds to the page through the `report` fixture:

```python
def test_reach(game, report, request):
    report.note("Ran right-handed.")  # a line about the whole run
    report.section("Placements", intro="each hand placed", columns=["Test", "Landed"])
    report.section("Placements", rows=[[request.node.name, "1.2 cm"]])  # the same title adds rows
    report.section("Perf", html="<pre>...</pre>")  # raw HTML instead of a table
    path = report.picture(request.node.nodeid, label="the panel")  # a file for the mod to write, shown if it does
    (report.folder / "perf.json").write_text("{}")  # a file beside the page
```

Sections show after the areas, in the order first added; a section is a table or HTML, and a call of the other shape,
other columns or a row of another length raises `ValueError`. `devbench.testing.report.render(record)` renders a
`Record` without a pytest session.

## Develop

```
pip install -e clients/python
pytest clients/python
```
