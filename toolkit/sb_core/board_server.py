"""Server HTTP locale della board: token, controllo dell'Host, routing e ciclo di vita."""
import datetime
import json
import os
import secrets
import signal
import sys
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .board_api import BoardError
from .errors import SbError, WikiError

HTML_PATH = Path(__file__).resolve().parents[1] / "board" / "index.html"
STATE_FILE = ".sb/board.json"
MAX_BODY = 1_000_000


class BoardApp(object):
    def __init__(self, board, token, html_path=HTML_PATH):
        self.board = board
        self.token = token
        self.html_path = html_path


class _Handler(BaseHTTPRequestHandler):
    server_version = "sb-board"

    def log_message(self, fmt, *args):  # niente log per ogni richiesta
        pass

    @property
    def app(self):
        return self.server.app

    def _send(self, status, payload=None, body=None, ctype="application/json; charset=utf-8"):
        data = body if body is not None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def _allowed(self):
        port = self.server.server_address[1]
        if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
            self._send(403, {"error": "host non ammesso"})
            return False
        if self.path.startswith("/api/"):
            given = self.headers.get("X-SB-Token") or ""
            if not secrets.compare_digest(given, self.app.token):
                self._send(403, {"error": "token mancante o non valido"})
                return False
        return True

    def _json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise BoardError("richiesta troppo grande")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            raise BoardError("JSON non valido")
        if not isinstance(data, dict):
            raise BoardError("atteso un oggetto JSON")
        return data

    def _dispatch(self, method):
        if not self._allowed():
            return
        route = self.path.split("?", 1)[0]
        board = self.app.board
        try:
            if method == "GET" and route == "/":
                return self._send(200, body=self.app.html_path.read_bytes(), ctype="text/html; charset=utf-8")
            if method == "GET" and route == "/api/snapshot":
                return self._send(200, board.snapshot())
            if method == "GET" and route == "/api/version":
                return self._send(200, board.version())
            if method == "POST" and route == "/api/tasks":
                return self._send(201, board.create(self._json_body()))
            if method == "PATCH" and route == "/api/tasks":
                return self._send(200, board.update(self._json_body()))
            self._send(404, {"error": "non trovato"})
        except BoardError as exc:
            self._send(exc.status, exc.payload)
        except SbError as exc:
            self._send(422, {"error": str(exc)})
        except Exception as exc:  # il server resta attivo
            traceback.print_exc(file=sys.stderr)
            self._send(500, {"error": f"errore interno: {type(exc).__name__}: {exc}"})

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PATCH(self):
        self._dispatch("PATCH")


def bind(port, attempts=10):
    candidates = [0] if port == 0 else range(port, port + attempts)
    last = None
    for candidate in candidates:
        try:
            return ThreadingHTTPServer(("127.0.0.1", candidate), _Handler)
        except OSError as exc:
            last = exc
    raise WikiError(f"nessuna porta libera tra {port} e {port + attempts - 1} ({last})")


def start(board, port=8765, token=None):
    server = bind(port)
    server.daemon_threads = True
    server.app = BoardApp(board, token or secrets.token_urlsafe(24))
    return server


def url_of(server):
    return f"http://127.0.0.1:{server.server_address[1]}/?t={server.app.token}"


def running_board(root):
    try:
        info = json.loads((Path(root) / STATE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    pid = info.get("pid") if isinstance(info, dict) else None
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        return info
    return info


def run(board, port=8765, open_browser=True, emit=None):
    emit = emit or (lambda data: print(json.dumps(data, ensure_ascii=False), flush=True))
    existing = running_board(board.root)
    if existing:
        emit(dict(existing, already_running=True))
        return {"stopped": False, "url": existing.get("url")}
    server = start(board, port)
    info = {
        "pid": os.getpid(),
        "port": server.server_address[1],
        "url": url_of(server),
        "started": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    state = board.root / STATE_FILE
    state.parent.mkdir(exist_ok=True)
    state.write_text(json.dumps(info), encoding="utf-8")
    emit(info)

    stop = threading.Event()

    def push_loop():
        while not stop.wait(5):
            board.pusher.tick()

    def on_signal(signum, frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    threading.Thread(target=push_loop, daemon=True).start()
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    if open_browser:
        webbrowser.open(info["url"])
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        stop.set()
        server.server_close()
        board.pusher.flush()
        try:
            state.unlink()
        except OSError:
            pass
    return {"stopped": True, "url": info["url"], "sync": board.pusher.state()}
