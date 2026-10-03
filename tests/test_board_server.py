import datetime
import json
import os
import signal
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request

from helpers import ROOT, WikiCase, md
from sb_core.board_api import Board, etag_of
from sb_core.board_server import KEY_FILE, STATE_FILE, load_key, running_board, start

TODAY = datetime.date(2026, 10, 2)
T = "operations/tasks/Stima.md"
FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi"),
    T: md('type: task\ntitle: Stima\nowner: "[[Luca Bianchi]]"\npriority: low'),
}


class ServerTest(WikiCase):
    def setUp(self):
        self.root = self.make_git_wiki(FILES)
        self.board = Board(self.root, today=lambda: TODAY)
        self.server = start(self.board, port=0, token="segreto")
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def call(self, method, path, body=None, token="segreto", host=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("X-SB-Token", token)
        if host:
            req.add_header("Host", host)
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                payload = res.read()
                kind = res.headers.get("Content-Type", "")
                return res.status, (json.loads(payload) if "json" in kind else payload.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")

    def etag(self):
        return etag_of((self.root / T).read_bytes())

    def test_page_is_served_without_token(self):
        status, page = self.call("GET", "/?t=segreto", token=None)
        self.assertEqual(status, 200)
        self.assertIn("<html", page)

    def test_api_requires_the_token(self):
        self.assertEqual(self.call("GET", "/api/snapshot", token=None)[0], 403)
        self.assertEqual(self.call("GET", "/api/snapshot", token="altro")[0], 403)
        status, snap = self.call("GET", "/api/snapshot")
        self.assertEqual((status, snap["tasks"][0]["title"]), (200, "Stima"))

    def test_host_header_is_checked(self):
        self.assertEqual(self.call("GET", "/", token=None, host="evil.example:80")[0], 403)
        self.assertEqual(self.call("GET", "/api/version", host="evil.example")[0], 403)
        self.assertEqual(self.call("GET", "/api/version", host=f"localhost:{self.port}")[0], 200)

    def test_patch_then_stale_etag(self):
        etag = self.etag()
        status, data = self.call("PATCH", "/api/tasks", {"path": T, "etag": etag, "set": {"priority": "high"}})
        self.assertEqual((status, data["task"]["priority"], data["committed"]), (200, "high", True))
        status, data = self.call("PATCH", "/api/tasks", {"path": T, "etag": etag, "set": {"priority": "medium"}})
        self.assertEqual((status, data["task"]["priority"]), (409, "high"))

    def test_concurrent_patches_with_the_same_etag(self):
        etag = self.etag()
        results = []

        def send(priority):
            results.append(self.call("PATCH", "/api/tasks", {"path": T, "etag": etag, "set": {"priority": priority}})[0])

        threads = [threading.Thread(target=send, args=(p,)) for p in ("high", "medium")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), [200, 409])

    def test_create_and_errors(self):
        status, data = self.call("POST", "/api/tasks", {"title": "Nuovo", "status": "blocked"})
        self.assertEqual((status, data["task"]["status"]), (201, "blocked"))
        status, data = self.call("POST", "/api/tasks", {"title": "Nuovo"})
        self.assertEqual((status, data["path"]), (409, "operations/tasks/Nuovo.md"))
        self.assertEqual(self.call("POST", "/api/tasks", {"title": "A: B"})[0], 422)
        self.assertEqual(self.call("PATCH", "/api/tasks", {"path": "operations/tasks/X.md", "set": {"a": 1}})[0], 404)
        self.assertEqual(self.call("POST", "/api/tasks", raw=b"non json")[0], 400)
        self.assertEqual(self.call("GET", "/api/altro")[0], 404)

    def test_version_endpoint(self):
        status, data = self.call("GET", "/api/version")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["version"]), 40)


class LifecycleTest(WikiCase):
    def launch(self, root):
        return subprocess.Popen(
            [sys.executable, str(ROOT / "toolkit" / "sb.py"), "board", "--no-open", "--port", "0", "--wiki", str(root)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

    def test_start_reuse_and_stop(self):
        root = self.make_git_wiki(FILES)
        proc = self.launch(root)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        info = json.loads(proc.stdout.readline())
        state = json.loads((root / STATE_FILE).read_text(encoding="utf-8"))
        self.assertEqual((state["pid"], state["url"]), (proc.pid, info["url"]))
        self.assertTrue(info["url"].startswith(f"http://127.0.0.1:{info['port']}/?t="))
        token = info["url"].split("?t=", 1)[1]
        req = urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/version", headers={"X-SB-Token": token})
        with urllib.request.urlopen(req, timeout=10) as res:
            self.assertEqual(res.status, 200)

        second = subprocess.run(
            [sys.executable, str(ROOT / "toolkit" / "sb.py"), "board", "--no-open", "--wiki", str(root)],
            capture_output=True, text=True, timeout=30,
        )
        again = json.loads(second.stdout.splitlines()[0])
        self.assertEqual((again["already_running"], again["url"]), (True, info["url"]))

        proc.send_signal(signal.SIGTERM)
        self.assertEqual(proc.wait(timeout=30), 0)
        self.assertFalse((root / STATE_FILE).exists())

    def test_url_survives_a_restart(self):
        # il preferito nel browser deve continuare a funzionare dopo un riavvio
        root = self.make_git_wiki(FILES)
        urls = []
        for _ in range(2):
            proc = self.launch(root)
            self.addCleanup(lambda p=proc: p.poll() is None and p.kill())
            urls.append(json.loads(proc.stdout.readline())["url"])
            proc.send_signal(signal.SIGTERM)
            self.assertEqual(proc.wait(timeout=30), 0)
        self.assertEqual(urls[0].split("?t=")[1], urls[1].split("?t=")[1])
        self.assertEqual(oct((root / KEY_FILE).stat().st_mode & 0o777), "0o600")
        self.assertNotIn("port", load_key(root))  # con --port 0 la porta non si ricorda

    def test_saved_port_is_reused(self):
        root = self.make_git_wiki(FILES)
        (root / ".sb").mkdir(exist_ok=True)
        probe = start(Board(root, today=lambda: TODAY), port=0)
        free = probe.server_address[1]
        probe.server_close()
        (root / KEY_FILE).write_text(json.dumps({"token": "x" * 32, "port": free}), encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / "toolkit" / "sb.py"), "board", "--no-open", "--wiki", str(root)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        info = json.loads(proc.stdout.readline())
        self.assertEqual(info["url"], f"http://127.0.0.1:{free}/?t={'x' * 32}")
        self.assertNotIn("warning", info)
        proc.send_signal(signal.SIGTERM)
        self.assertEqual(proc.wait(timeout=30), 0)

    def test_broken_key_file_is_ignored(self):
        root = self.make_wiki(FILES)
        (root / ".sb").mkdir(exist_ok=True)
        (root / KEY_FILE).write_text('{"token": "corto", "port": "8765"}', encoding="utf-8")
        self.assertEqual(load_key(root), {})

    def test_stale_state_file_is_ignored(self):
        root = self.make_wiki(FILES)
        (root / ".sb").mkdir(exist_ok=True)
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        (root / STATE_FILE).write_text(json.dumps({"pid": dead.pid, "url": "http://vecchio"}), encoding="utf-8")
        self.assertIsNone(running_board(root))


if __name__ == "__main__":
    unittest.main()
