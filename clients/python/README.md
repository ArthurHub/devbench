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

## Develop

```
pip install -e clients/python
pytest clients/python
```
