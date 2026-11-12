"""Local web server for the fast chat tutor page (stdlib only)."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any

from . import load_known
from .chat import MODELS, Tutor

DEFAULT_PORT = 8790
_MAX_BODY_BYTES = 16_000
_MAX_TEXT_CHARS = 500


def request_allowed(
    *, method: str, host: str | None, origin: str | None, content_type: str | None, port: int
) -> bool:
    """Only this page may use the server; other sites would spend Claude and MiniMax usage.

    The Host check blocks DNS rebinding; requiring JSON on POST forces a CORS
    preflight that this server never grants, so cross-site form posts fail.
    """
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    if host not in allowed_hosts:
        return False
    if origin and origin.removeprefix("http://") not in allowed_hosts:
        return False
    if method == "POST":
        return (content_type or "").split(";")[0].strip() == "application/json"
    return True


def serve(port: int = DEFAULT_PORT) -> None:
    tutor = Tutor(load_known)
    page = files(__package__).joinpath("page.html").read_bytes()

    def state() -> dict[str, object]:
        return {**tutor.store.snapshot(), "models": MODELS}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
            pass

        def _allowed(self) -> bool:
            ok = request_allowed(
                method=self.command,
                host=self.headers.get("Host"),
                origin=self.headers.get("Origin"),
                content_type=self.headers.get("Content-Type"),
                port=port,
            )
            if not ok:
                self.send_error(HTTPStatus.FORBIDDEN)
            return ok

        def _json(self, body: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if not 0 <= length <= _MAX_BODY_BYTES:
                raise ValueError("request too large")
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("expected a JSON object")
            return body

        def _text(self, body: dict[str, Any]) -> str:
            text = str(body.get("text", "")).strip()
            if not text or len(text) > _MAX_TEXT_CHARS:
                raise ValueError(f"text must be 1-{_MAX_TEXT_CHARS} characters")
            return text

        def do_GET(self) -> None:
            if not self._allowed():
                return
            if self.path == "/":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page)
            elif self.path == "/api/state":
                self._json(state())
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if not self._allowed():
                return
            try:
                body = self._body()
                if self.path == "/api/send":
                    chat_id = body.get("chat")
                    self._stream_turn(
                        self._text(body), chat_id if isinstance(chat_id, str) else None
                    )
                elif self.path == "/api/model":
                    tutor.set_model(str(body.get("model")))
                    self._json({"model": tutor.model})
                elif self.path == "/api/new":
                    tutor.new_chat()
                    self._json(state())
                elif self.path == "/api/open":
                    tutor.open_chat(str(body.get("id")))
                    self._json(state())
                elif self.path == "/api/replay":
                    tutor.speaker.say(self._text(body))
                    self._json({"ok": True})
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
            except ValueError as error:
                self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            except RuntimeError as error:
                self._json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def _stream_turn(self, text: str, chat_id: str | None) -> None:
            if chat_id is not None and chat_id not in tutor.store.chats:
                raise ValueError("no such chat")
            turn = tutor.turn(text, chat_id)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                for event in turn:
                    self.wfile.write((json.dumps(event, ensure_ascii=False) + "\n").encode())
                    self.wfile.flush()
            except RuntimeError as error:
                line = json.dumps({"t": "error", "message": str(error)}, ensure_ascii=False)
                self.wfile.write((line + "\n").encode())
            except OSError:
                pass  # the page went away; the next turn replaces the unfinished process
            finally:
                turn.close()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Chinese tutor on http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
