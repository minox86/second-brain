"""Operazioni git della board: commit dei soli file toccati e push raggruppato."""
import datetime
import subprocess
import time
from pathlib import Path


class Git(object):
    def __init__(self, root):
        self.root = Path(root)

    def _run(self, *args):
        return subprocess.run(["git", *args], cwd=str(self.root), capture_output=True, text=True)

    def is_repo(self):
        proc = self._run("rev-parse", "--is-inside-work-tree")
        return proc.returncode == 0 and proc.stdout.strip() == "true"

    def head(self):
        proc = self._run("rev-parse", "--short", "HEAD")
        return proc.stdout.strip() if proc.returncode == 0 else None

    def has_remote(self):
        proc = self._run("remote")
        return proc.returncode == 0 and bool(proc.stdout.strip())

    def commit(self, paths, message):
        """Commit dei soli `paths` (relativi alla radice), cancellazioni comprese."""
        if not self.is_repo():
            return False, "la wiki non è un repository git"
        paths = sorted(set(paths))
        tracked = set(self._run("ls-files", "--", *paths).stdout.splitlines()) if paths else set()
        selected = [p for p in paths if (self.root / p).exists() or p in tracked]
        if not selected:
            return True, None
        added = self._run("add", "-A", "--", *selected)
        if added.returncode != 0:
            return False, added.stderr.strip()
        if self._run("diff", "--cached", "--quiet", "--", *selected).returncode == 0:
            return True, None
        proc = self._run("commit", "-q", "-m", message, "--", *selected)
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout).strip()
        return True, None

    def push(self):
        upstream = self._run("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        args = ("push", "-q") if upstream.returncode == 0 else ("push", "-q", "-u", "origin", "HEAD")
        proc = self._run(*args)
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout).strip()
        return True, None


class PushScheduler(object):
    """Push al massimo una volta ogni `interval` secondi; flush all'arresto."""

    def __init__(self, git, interval=60, clock=time.monotonic):
        self.git = git
        self.interval = interval
        self.clock = clock
        self.pending = False
        self.last_push = None
        self.last_error = None
        self._last_attempt = None

    def mark(self):
        self.pending = True

    def tick(self):
        if self.pending and (self._last_attempt is None or self.clock() - self._last_attempt >= self.interval):
            self._attempt()

    def flush(self):
        if self.pending:
            self._attempt()

    def _attempt(self):
        self._last_attempt = self.clock()
        if not self.git.has_remote():
            self.pending = False
            return
        ok, error = self.git.push()
        if ok:
            self.pending = False
            self.last_push = datetime.datetime.now().isoformat(timespec="seconds")
            self.last_error = None
        else:
            self.last_error = error

    def state(self):
        return {"pending_push": self.pending, "last_push": self.last_push, "last_error": self.last_error}
