# 03 Events

Status: resolved
Blocked by: 02

Spec: [../spec.md](../spec.md). Source: `Events`, `head_seq`, `events_since` in the flashlight suite's `devbench.py`.

## What

`devbench.events.Events(bench, prefix=None)`: starts at the head seq; `all(topic=None)`; `wait(topic, timeout, where)`.
A topic matches bare or as `<prefix>.<topic>` (a mod's events). `Devbench.head_seq()` / `events_since(seq)` on the
client.

## Acceptance

Unit tests against the fake server: events before the start are not seen, a prefixed topic matches bare, `wait`
returns the first match of `where`, and times out with the topic in the message.
