"""Local web server for the fast chat tutor page (stdlib only)."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any

from . import load_known
from .chat import MODELS, Tutor, history

DEFAULT_PORT = 8790


def serve(port: int = DEFAULT_PORT) -> None:
    tutor = Tutor(load_known)
    page = files(__package__).joinpath("page.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
            pass

        def _json(self, body: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:
            if self.path == "/":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page)
            elif self.path == "/api/state":
                self._json({"model": tutor.model, "models": MODELS, "history": history()})
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            body = self._body()
            try:
                if self.path == "/api/send":
                    self._stream_turn(str(body.get("text", "")).strip())
                elif self.path == "/api/model":
                    tutor.set_model(str(body.get("model")))
                    self._json({"model": tutor.model})
                elif self.path == "/api/new":
                    tutor.new_chat()
                    self._json({"ok": True})
                elif self.path == "/api/replay":
                    tutor.speaker.say(str(body.get("text", "")))
                    self._json({"ok": True})
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
            except ValueError as error:
                self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _stream_turn(self, text: str) -> None:
            if not text:
                raise ValueError("empty message")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                for event in tutor.turn(text):
                    self.wfile.write((json.dumps(event, ensure_ascii=False) + "\n").encode())
                    self.wfile.flush()
            except RuntimeError as error:
                line = json.dumps({"t": "error", "message": str(error)}, ensure_ascii=False)
                self.wfile.write((line + "\n").encode())

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Chinese tutor on http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
