"""A fake devbench for the client's unit tests: a local HTTP server that answers from scripted responses, no game."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

# A scripted tool: takes the call's arguments, returns the answer (200) or (status, answer). An answer of bytes is
# sent as is, as text/plain, to stand for a body that is not JSON.
ToolHandler = Callable[[dict[str, Any]], Any]


class FakeDevbench:
    """
    Answers /api/tool/<name> from tools, /api/health from health and /api/events?since=<seq> from events, on a free
    port of 127.0.0.1 with HTTP/1.1 keep-alive. calls records each request as (method, path, body); connections
    counts the TCP connections accepted. drop_next() closes the socket after the next answer, as a restarting game does.
    """

    def __init__(self) -> None:
        self.tools: dict[str, ToolHandler] = {}
        self.health: Any = {"ok": True}
        self.events: list[dict[str, Any]] = []
        self.calls: list[tuple[str, str, Any]] = []
        self.connections = 0
        self._drop = False
        self._lock = threading.Lock()
        handler = type("Handler", (_Handler,), {"fake": self})
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._server.daemon_threads = True
        self.port: int = self._server.server_address[1]
        # a short poll so close() (shutdown) does not wait out the default 0.5 s per test
        self._thread = threading.Thread(target=self._server.serve_forever, args=(0.02,), daemon=True)
        self._thread.start()

    def drop_next(self) -> None:
        """Close the kept-alive socket right after the next answer, without telling the client."""
        with self._lock:
            self._drop = True

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()

    def _take_drop(self) -> bool:
        with self._lock:
            drop, self._drop = self._drop, False
            return drop

    def _count_connection(self) -> None:
        with self._lock:
            self.connections += 1

    def _record(self, method: str, path: str, body: Any) -> None:
        with self._lock:
            self.calls.append((method, path, body))


class _Handler(BaseHTTPRequestHandler):
    """One connection to the fake; fake is set on the subclass FakeDevbench makes."""

    protocol_version = "HTTP/1.1"
    fake: FakeDevbench

    def setup(self) -> None:
        super().setup()
        self.fake._count_connection()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - the base class names it so
        pass

    def do_GET(self) -> None:
        url = urlsplit(self.path)
        self.fake._record("GET", self.path, None)
        if url.path == "/api/health":
            self._answer(self.fake.health)
        elif url.path == "/api/events":
            since = int(parse_qs(url.query).get("since", ["0"])[0])
            events = self.fake.events
            head = events[-1]["seq"] if events else 0
            self._answer({"headSeq": head, "events": [event for event in events if event["seq"] > since]})
        else:
            self._answer((404, {"ok": False, "error": f"no route {url.path}"}))

    def do_POST(self) -> None:
        url = urlsplit(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        self.fake._record("POST", self.path, body)
        name = url.path.removeprefix("/api/tool/")
        handler = self.fake.tools.get(name) if url.path.startswith("/api/tool/") else None
        if handler is None:
            self._answer((404, {"ok": False, "error": f"unknown tool {name}"}))
        else:
            self._answer(handler(body))

    def _answer(self, result: Any) -> None:
        """Send a scripted result: an answer (200) or (status, answer); bytes go out as plain text."""
        status, answer = result if isinstance(result, tuple) else (200, result)
        if isinstance(answer, bytes):
            data, content_type = answer, "text/plain"
        else:
            data, content_type = json.dumps(answer).encode("utf-8"), "application/json"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        self.wfile.flush()
        if self.fake._take_drop():
            self.close_connection = True
