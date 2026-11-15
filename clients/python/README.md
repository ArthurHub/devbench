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

## Develop

```
pip install -e clients/python
pytest clients/python
```
