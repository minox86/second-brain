"""Logica della board dei task: snapshot e modifiche deterministiche, senza HTTP.

Ogni modifica segue le regole della spec della board (§5): valori espliciti,
frontmatter toccato solo nei campi indicati, validazione con ripristino,
commit dei soli file toccati.
"""
import datetime
import hashlib
import threading

from .errors import SbError
from .gitops import Git, PushScheduler
from .names import norm
from .tasks import list_tasks, task_record
from .wiki import Wiki, closed_statuses, parse_date

DEFAULT_STATUS = ["todo", "doing", "blocked", "done", "dropped"]
DEFAULT_PRIORITY = ["low", "medium", "high"]


class BoardError(SbError):
    """Errore con codice HTTP e payload JSON."""
    status = 400

    def __init__(self, message, **payload):
        super().__init__(message)
        self.payload = dict(payload, error=message)


class NotFound(BoardError):
    status = 404


class Conflict(BoardError):
    status = 409


class Invalid(BoardError):
    status = 422


def etag_of(data):
    return hashlib.sha1(data).hexdigest()


def _iso(value):
    date = parse_date(value)
    return date.isoformat() if date else None


class Board(object):
    def __init__(self, wiki_path, today=None, push_interval=60):
        self.wiki = Wiki(wiki_path)
        self.root = self.wiki.root
        self.git = Git(self.root)
        self.pusher = PushScheduler(self.git, interval=push_interval)
        self.lock = threading.Lock()
        self.pending_commit = set()
        self.last_commit_error = None
        self._today = today

    def today(self):
        return self._today() if self._today else datetime.date.today()

    def refresh(self):
        """Rilegge schema e pagine: la wiki può essere cambiata da fuori."""
        self.wiki = Wiki(self.root)
        return self.wiki

    def enums(self, wiki):
        typedef = wiki.types["task"]
        status = (typedef.fields.get("status") or {}).get("values") or DEFAULT_STATUS
        priority = (typedef.fields.get("priority") or {}).get("values") or DEFAULT_PRIORITY
        return {"status": list(status), "priority": list(priority), "closed": list(closed_statuses(typedef))}

    def snapshot(self):
        wiki = self.refresh()
        today = self.today()
        return {
            "wiki": {"name": self.root.name, "root": str(self.root)},
            "today": today.isoformat(),
            "thresholds": dict(wiki.thresholds),
            "enums": self.enums(wiki),
            "tasks": [self._decorate(wiki, r) for r in list_tasks(wiki, view="all", today=today)],
            "people": self._pages_of(wiki, "person", active_only=True),
            "projects": self._pages_of(wiki, "project"),
            "sync": self.sync_state(),
        }

    def version(self):
        digest = hashlib.sha1((self.git.head() or "").encode("utf-8"))
        folder = self.root / self.wiki.types["task"].folder
        if folder.is_dir():
            for path in sorted(folder.glob("*.md")):
                digest.update(path.name.encode("utf-8"))
                digest.update(str(path.stat().st_mtime_ns).encode("ascii"))
        return {"version": digest.hexdigest()}

    def sync_state(self):
        state = {
            "git": self.git.is_repo(),
            "head": self.git.head(),
            "uncommitted": sorted(self.pending_commit),
            "commit_error": self.last_commit_error,
        }
        state.update(self.pusher.state())
        return state

    def _pages_of(self, wiki, type_name, active_only=False):
        typedef = wiki.types.get(type_name)
        if typedef is None:
            return []
        closed = closed_statuses(typedef)
        pages = []
        for page in wiki.pages():
            if page.meta is None or page.type != type_name:
                continue
            status = page.meta.get("status")
            if active_only and status is not None and status in closed:
                continue
            pages.append({"title": page.title, "path": page.path})
        return sorted(pages, key=lambda p: norm(p["title"]))

    def _decorate(self, wiki, record):
        page = wiki.page(record["path"])
        record = dict(record)
        record["body"] = page.body if page else ""
        record["updated"] = _iso((page.meta or {}).get("updated")) if page else None
        record["etag"] = etag_of((self.root / record["path"]).read_bytes())
        return record

    def _record(self, rel):
        wiki = self.refresh()
        page = wiki.page(rel)
        record = task_record(page, self.today(), closed_statuses(wiki.types["task"]))
        return self._decorate(wiki, record)
