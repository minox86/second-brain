"""Board sempre accesa su macOS: un LaunchAgent la avvia al login e la riavvia se cade."""
import hashlib
import os
import plistlib
import signal
import subprocess
import sys
import time
from pathlib import Path

from .board_server import STATE_FILE, running_board
from .errors import WikiError

SB_PY = Path(__file__).resolve().parents[1] / "sb.py"
LOG_FILE = ".sb/board.log"


def label_of(root):
    digest = hashlib.sha1(str(Path(root).resolve()).encode("utf-8")).hexdigest()[:10]
    return f"com.second-brain.board.{digest}"


def plist_path(root, home=None):
    return Path(home or Path.home()) / "Library" / "LaunchAgents" / f"{label_of(root)}.plist"


def agent_plist(root, python=None, path_env=None):
    root = Path(root).resolve()
    log = str(root / LOG_FILE)
    return {
        "Label": label_of(root),
        "ProgramArguments": [python or sys.executable, str(SB_PY), "board", "--no-open", "--wiki", str(root)],
        "WorkingDirectory": str(root),
        "RunAtLoad": True,
        # riavvia solo se cade: se trova un'altra board già accesa esce con 0 e resta ferma
        "KeepAlive": {"SuccessfulExit": False},
        "ThrottleInterval": 10,
        # launchd parte con un PATH minimo: serve quello dell'utente per git e le credenziali
        "EnvironmentVariables": {"PATH": path_env if path_env is not None else os.environ.get("PATH", "/usr/bin:/bin")},
        "StandardOutPath": log,
        "StandardErrorPath": log,
    }


def _launchctl(*args):
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def _domain():
    return f"gui/{os.getuid()}"


def _stop_running(root, timeout=10):
    info = running_board(root)
    if not info:
        return False
    os.kill(info["pid"], signal.SIGTERM)
    deadline = time.time() + timeout
    while time.time() < deadline and (Path(root) / STATE_FILE).exists():
        time.sleep(0.2)
    return True


def _require_macos():
    if sys.platform != "darwin":
        raise WikiError("la board sempre accesa è disponibile solo su macOS (launchd)")


def install(root, launchctl=_launchctl):
    _require_macos()
    root = Path(root).resolve()
    target = plist_path(root)
    launchctl("bootout", f"{_domain()}/{label_of(root)}")  # reinstallazione: ignora se non c'era
    stopped = _stop_running(root)  # la board avviata a mano lascia il posto a quella dell'agente
    target.parent.mkdir(parents=True, exist_ok=True)
    (root / ".sb").mkdir(exist_ok=True)
    target.write_bytes(plistlib.dumps(agent_plist(root)))
    result = launchctl("bootstrap", _domain(), str(target))
    if result.returncode != 0:
        raise WikiError(f"launchctl bootstrap fallito: {(result.stderr or result.stdout).strip()}")
    info = None
    for _ in range(50):
        info = running_board(root)
        if info:
            break
        time.sleep(0.2)
    return {"installed": True, "label": label_of(root), "plist": str(target), "stopped_manual_board": stopped,
            "url": info.get("url") if info else None, "log": str(root / LOG_FILE)}


def uninstall(root, launchctl=_launchctl):
    _require_macos()
    root = Path(root).resolve()
    target = plist_path(root)
    existed = target.exists()
    launchctl("bootout", f"{_domain()}/{label_of(root)}")
    if existed:
        target.unlink()
    return {"uninstalled": existed, "label": label_of(root), "plist": str(target)}
