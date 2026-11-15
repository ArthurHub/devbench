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
        hands.head("down")  # "ready", "down" or {pitch?, yaw?, lookAt?, ...}
        hands.tap("left")  # press("left", ["trigger"], 100); returns once released
        hands.long_press("right", ["grip"])  # 1000 ms
        hands.rest()  # hands and head back in the ready pose
        hands.pose(hands={"right": {"node": "LArm_Hand", "front": 10}})  # any other pose arguments
```

Hands are physical (`left` / `right`); a mod maps its own primary / offhand. `pitch` and `yaw` pass through as the
`input` tool takes them. `TAP_MS` (100) and `LONG_PRESS_MS` (1000) are F4VR-CommonFramework's gesture thresholds.
A press without a hold of this owner (it never started, or the hold ran out) raises `DevbenchError` (409). `stop`
ignores a refused stop, and on an exception inside the `with` it never hides that exception.

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

## Develop

```
pip install -e clients/python
pytest clients/python
```
