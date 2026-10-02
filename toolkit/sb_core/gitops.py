"""Operazioni git della board: commit dei soli file toccati e push raggruppato."""
import datetime
import os
import subprocess
import threading
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
        tracked = self._tracked(paths)
        selected = [p for p in paths if p in tracked or self._on_disk(p)]
        if not selected:
            return True, None
        # rinomine che cambiano solo maiuscole/minuscole (filesystem case-insensitive):
        # togli dall'indice la vecchia grafia, così git aggiunge quella nuova
        for path in selected:
            if path in tracked and not self._on_disk(path):
                continue
            for other in selected:
                if other != path and other.lower() == path.lower() and other in tracked and other not in self._disk_names(other):
                    self._run("rm", "--cached", "-q", "--ignore-unmatch", "--", other)
        added = self._run("add", "-A", "--", *selected)
        if added.returncode != 0:
            return False, added.stderr.strip()
        if self._run("diff", "--cached", "--quiet", "--", *selected).returncode == 0:
            return True, None
        staged = self._run("-c", "core.quotePath=false", "diff", "--cached", "--no-renames", "--name-only", "-z").stdout
        others = {p for p in staged.split("\0") if p} - set(selected)
        if others:
            # l'utente ha altro in stage: committa solo i nostri path
            proc = self._run("commit", "-q", "-m", message, "--", *selected)
        else:
            # l'indice contiene solo i nostri file: commit dell'indice così com'è
            # (necessario per le rinomine che cambiano solo maiuscole/minuscole)
            proc = self._run("commit", "-q", "-m", message)
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout).strip()
        return True, None

    def _tracked(self, paths):
        if not paths:
            return set()
        out = self._run("-c", "core.quotePath=false", "ls-files", "-z", "--", *paths).stdout
        return {p for p in out.split("\0") if p}

    def _disk_names(self, path):
        """Nomi reali (con le maiuscole come sono su disco) nella cartella di `path`."""
        folder = (self.root / path).parent
        if not folder.is_dir():
            return set()
        prefix = path.rsplit("/", 1)[0] + "/" if "/" in path else ""
        return {prefix + name for name in os.listdir(str(folder))}

    def _on_disk(self, path):
        """Esiste con esattamente questa grafia (anche su filesystem case-insensitive)."""
        return path in self._disk_names(path)

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
        self._generation = 0
        self._lock = threading.Lock()

    def mark(self):
        with self._lock:
            self._generation += 1
            self.pending = True

    def tick(self):
        if self.pending and (self._last_attempt is None or self.clock() - self._last_attempt >= self.interval):
            self._attempt()

    def flush(self):
        if self.pending:
            self._attempt()

    def _attempt(self):
        with self._lock:
            self._last_attempt = self.clock()
            started = self._generation
        if not self.git.has_remote():
            with self._lock:
                if self._generation == started:
                    self.pending = False
            return
        ok, error = self.git.push()
        with self._lock:
            if ok:
                # un mark() arrivato durante il push lascia il push successivo in sospeso
                if self._generation == started:
                    self.pending = False
                self.last_push = datetime.datetime.now().isoformat(timespec="seconds")
                self.last_error = None
            else:
                self.last_error = error

    def state(self):
        return {"pending_push": self.pending, "last_push": self.last_push, "last_error": self.last_error}
