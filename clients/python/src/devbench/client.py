"""The running game through devbench's REST port: find the port, call its tools, check its health.

One kept-alive connection serves every call: a connection per call uses up the local ports in seconds when a test
polls.
"""

from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
from typing import Any

# devbench binds only the loopback interface
HOST = "127.0.0.1"

# the port each game's devbench is configured with, by (game, vr)
DEFAULT_PORTS = {
    ("skyrim", False): 8920,
    ("skyrim", True): 8921,
    ("fallout4", False): 8930,
    ("fallout4", True): 8931,
}


class DevbenchError(Exception):
    """
    A call that devbench or a tool refused, with the error it gave.
    tool, status and answer hold the tool name (None for a non-tool endpoint), the HTTP status and the decoded answer.
    """

    def __init__(self, message: str, *, tool: str | None = None, status: int | None = None, answer: Any = None) -> None:
        super().__init__(message)
        self.tool = tool
        self.status = status
        self.answer = answer


def _state_dir_id(game: str, vr: bool) -> str:
    """
    The %LOCALAPPDATA%/devbench subfolder of a game, as src/core/Server.cpp names it:
    se / vr for Skyrim, fallout4 / fallout4vr for Fallout 4.
    """
    if game == "skyrim":
        return "vr" if vr else "se"
    return game + ("vr" if vr else "")


def find_port(game: str, vr: bool) -> int:
    """
    The port a game's devbench bound, from the runtime.json it writes under %LOCALAPPDATA%/devbench/<id>/, or the
    game's default port when there is no readable one. game is "skyrim" or "fallout4"; anything else raises ValueError.
    """
    key = (game, bool(vr))
    if key not in DEFAULT_PORTS:
        raise ValueError(f"unknown game {game!r}: expected 'skyrim' or 'fallout4'")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        runtime = Path(local) / "devbench" / _state_dir_id(game, bool(vr)) / "runtime.json"
        try:
            port = int(json.loads(runtime.read_text(encoding="utf-8"))["port"])
            if 1 <= port <= 65535:
                return port
        except (OSError, ValueError, KeyError, TypeError):
            pass
    return DEFAULT_PORTS[key]


def _decode(status: int, raw: bytes, what: str, tool: str | None) -> Any:
    """
    The JSON answer of a response; an empty body is {}. A body that is not JSON (a crash page, a plain-text 404)
    raises DevbenchError with the status and the start of the text.
    """
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        text = raw[:200].decode("utf-8", errors="replace")
        raise DevbenchError(f"{what}: HTTP {status}, not JSON: {text!r}", tool=tool, status=status) from None


class Devbench:
    """A client of devbench's REST port on 127.0.0.1. Close it, or use it as a context manager."""

    def __init__(self, port: int, timeout: float = 60.0) -> None:
        self.port = port
        self.timeout = timeout
        self._connection: http.client.HTTPConnection | None = None

    def __enter__(self) -> Devbench:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    def _request(self, method: str, path: str, body: Any = None) -> tuple[int, bytes]:
        """
        Send one request on the kept-alive connection and return the status and the raw body. Only a reused
        connection the game dropped (it restarted, or closed an idle socket) is opened again and sent once more: the
        game never ran that request. A timeout is not retried, since the game may still be running the call.
        """
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        while True:
            if self._connection is None:
                self._connection = http.client.HTTPConnection(HOST, self.port, timeout=self.timeout)
            # http.client reopens by itself after a response that closed the socket; that send is not on a reused one
            reused = self._connection.sock is not None
            try:
                self._connection.request(method, path, body=payload, headers=headers)
                response = self._connection.getresponse()
                return response.status, response.read()
            except ConnectionError:
                self.close()
                if not reused:
                    raise
            except (http.client.HTTPException, OSError):
                self.close()
                raise

    def tool(self, name: str, /, **args: Any) -> dict[str, Any]:
        """
        Call a tool with its arguments and return its answer. A non-200 status or an answer with ok: false raises
        DevbenchError. name is positional-only, so a tool argument called name passes through.
        """
        status, raw = self._request("POST", f"/api/tool/{name}", args)
        label = " ".join(part for part in (name, str(args.get("action", ""))) if part)
        answer = _decode(status, raw, label, name)
        if status != 200 or not isinstance(answer, dict) or answer.get("ok") is False:
            error = answer.get("error", answer) if isinstance(answer, dict) else answer
            raise DevbenchError(f"{label}: {error}", tool=name, status=status, answer=answer)
        return answer

    def health(self) -> dict[str, Any]:
        """devbench's own liveness answer (GET /api/health); a non-200 status raises DevbenchError."""
        status, raw = self._request("GET", "/api/health")
        answer = _decode(status, raw, "health", None)
        if status != 200:
            raise DevbenchError(f"health: HTTP {status} {answer}", status=status, answer=answer)
        return answer


class ModTool:
    """A mod's own devbench tool, called by action. The mod's events carry the tool name as their topic prefix."""

    def __init__(self, bench: Devbench, name: str) -> None:
        self.bench = bench
        self.name = name

    @property
    def prefix(self) -> str:
        """The topic prefix of the mod's events: its tool name."""
        return self.name

    def call(self, action: str, /, **args: Any) -> dict[str, Any]:
        """Call an action of the tool; a refusal raises DevbenchError."""
        return self.bench.tool(self.name, action=action, **args)

    def health(self) -> dict[str, Any]:
        """The tool's health action: the mod's version and the actions it offers."""
        return self.call("health")
