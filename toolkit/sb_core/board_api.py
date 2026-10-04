"""Logica della board dei task: snapshot e modifiche deterministiche, senza HTTP.

Ogni modifica segue le regole della spec della board (§5): valori espliciti,
frontmatter toccato solo nei campi indicati, validazione con ripristino,
commit dei soli file toccati.
"""
import datetime
import hashlib
import threading

from .errors import PlanError, SbError
from .frontmatter import render, update_text
from .gitops import Git, PushScheduler
from .index import write_index
from .links import link_target_name
from .log import append_log
from .migrate import migrate
from .names import norm, title_problem
from .tasks import list_tasks, task_record
from .validate import validate
from .wiki import PAGE_ROOTS, Wiki, closed_statuses, parse_date

DEFAULT_STATUS = ["todo", "blocked", "done", "dropped"]
DEFAULT_PRIORITY = ["low", "medium", "high"]
EDITABLE = ("title", "status", "owner", "due", "priority", "related")
FIELD_ORDER = ("status", "owner", "due", "priority", "related")


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


def _describe(value):
    if value is None:
        return "∅"
    if isinstance(value, list):
        return ", ".join(link_target_name(v) or v for v in value) or "∅"
    return link_target_name(value) or str(value)


def _one_line(text):
    return " ".join(str(text or "").split())


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
            "wiki": {"name": wiki.name, "root": str(self.root)},
            "today": today.isoformat(),
            "thresholds": dict(wiki.thresholds),
            "enums": self.enums(wiki),
            "tasks": [self._decorate(wiki, r) for r in list_tasks(wiki, view="all", today=today)
                      if wiki.page(r["path"]).meta.get("archived") is not True],
            "people": self._pages_of(wiki, "person", active_only=True),
            "projects": self._pages_of(wiki, "project"),
            "page_types": self._page_types(wiki),
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

    def _page_types(self, wiki):
        """Titolo -> tipo di ogni pagina: la board ne ricava icona ed etichetta dei collegati."""
        types = {}
        for page in wiki.pages():
            if page.meta is not None and page.type:
                types.setdefault(page.title, page.type)
        return types

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
        sources = (page.meta or {}).get("sources") if page else None
        record["sources"] = [x for x in sources if isinstance(x, str)] if isinstance(sources, list) else []
        record["etag"] = etag_of((self.root / record["path"]).read_bytes())
        return record

    def _record(self, rel):
        wiki = self.refresh()
        page = wiki.page(rel)
        record = task_record(page, self.today(), closed_statuses(wiki.types["task"]))
        return self._decorate(wiki, record)

    # scrittura

    def create(self, data):
        with self.lock:
            wiki = self.refresh()
            title = _one_line(data.get("title"))
            problem = title_problem(title)
            if problem:
                raise Invalid(f"titolo non valido: {problem}")
            _, existing = wiki.lookup(title)
            if existing:
                raise Conflict(f"esiste già una pagina '{existing[0].title}'", path=existing[0].path)
            given = {k: data.get(k) for k in FIELD_ORDER if data.get(k) not in (None, "", [])}
            fields = self._normalize(wiki, given)
            today = self.today().isoformat()
            meta = {"type": "task", "title": title}
            for key in FIELD_ORDER:
                if fields.get(key) is not None:
                    meta[key] = fields[key]
            meta["created"] = today
            note = _one_line(data.get("note"))
            body = f"- {today}: {note}\n" if note else ""
            rel = f"{wiki.types['task'].folder}/{title}.md"
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render(meta, body), encoding="utf-8")
            errors = self._new_errors(rel, set())
            if errors:
                path.unlink()
                self.refresh()
                raise Invalid("il task non è valido", issues=errors)
            committed = self._close([rel], f"{title} → creato")
            return {"task": self._record(rel), "committed": committed}

    def update(self, data):
        with self.lock:
            wiki = self.refresh()
            rel = data.get("path")
            page = wiki.page(rel) if isinstance(rel, str) else None
            if page is None or page.type != "task":
                raise NotFound(f"task non trovato: {rel}")
            file = self.root / rel
            original = file.read_bytes()
            if data.get("etag") is not None and data["etag"] != etag_of(original):
                raise Conflict("il task è stato modificato altrove", task=self._record(rel))
            changes = dict(data.get("set") or {})
            new_title = changes.pop("title", None)
            new_title = _one_line(new_title) if new_title is not None else None
            if new_title == page.title:
                new_title = None
            fields = self._normalize(wiki, changes)
            note = _one_line(data.get("note"))
            if not fields and not note and not new_title:
                raise Invalid("nessuna modifica richiesta")
            if new_title is not None and title_problem(new_title):
                raise Invalid(f"titolo non valido: {title_problem(new_title)}")
            before = self._error_keys(wiki, rel)
            full = new_title is not None
            backup = self._backup() if full else {rel: original}
            today = self.today().isoformat()
            touched = {rel}
            try:
                text = update_text(original.decode("utf-8"), dict(fields, updated=today))
                if note:
                    text = text.rstrip("\n") + f"\n- {today}: {note}\n"
                file.write_text(text, encoding="utf-8")
                if new_title:
                    result = migrate(self.refresh(), [{"op": "retitle", "path": rel, "title": new_title}])
                    rel = result["changes"][0]["to"]
                    touched |= set(result["written"]) | {rel}
                errors = self._new_errors(rel, before)
            except PlanError as exc:
                self._restore(backup, full)
                raise Invalid(str(exc))
            if errors:
                self._restore(backup, full)
                raise Invalid("la modifica non è valida", issues=errors)
            committed = self._close(sorted(touched), self._summary(page.title, fields, note, new_title))
            return {"task": self._record(rel), "committed": committed}

    def archive(self):
        """Segna `archived: true` su tutti i task chiusi non ancora archiviati, in un solo commit."""
        with self.lock:
            wiki = self.refresh()
            closed = closed_statuses(wiki.types["task"])
            targets = sorted(p.path for p in wiki.pages()
                             if p.meta is not None and p.type == "task"
                             and p.meta.get("status") in closed and p.meta.get("archived") is not True)
            if not targets:
                return {"archived": 0, "committed": False}
            before = {(i.path, i.code, i.message) for i in validate(wiki, targets) if i.severity == "error"}
            backup = {rel: (self.root / rel).read_bytes() for rel in targets}
            today = self.today().isoformat()
            for rel, data in backup.items():
                text = update_text(data.decode("utf-8"), {"archived": True, "updated": today})
                (self.root / rel).write_text(text, encoding="utf-8")
            errors = [i.to_dict() for i in validate(self.refresh(), targets)
                      if i.severity == "error" and (i.path, i.code, i.message) not in before]
            if errors:
                self._restore(backup, False)
                raise Invalid("l'archiviazione non è valida", issues=errors)
            committed = self._close(targets, f"archiviati {len(targets)} task chiusi")
            return {"archived": len(targets), "committed": committed}

    def _normalize(self, wiki, fields):
        enums = self.enums(wiki)
        out = {}
        for key, value in fields.items():
            if key not in EDITABLE or key == "title":
                raise Invalid(f"campo non modificabile: {key}")
            if value is None or value == "" or value == []:
                out[key] = None
            elif key == "status":
                if value not in enums["status"]:
                    raise Invalid(f"stato non ammesso: {value} ({', '.join(enums['status'])})")
                out[key] = value
            elif key == "priority":
                if value not in enums["priority"]:
                    raise Invalid(f"priorità non ammessa: {value} ({', '.join(enums['priority'])})")
                out[key] = value
            elif key == "due":
                date = parse_date(value)
                if date is None or not 1900 <= date.year <= 2999:
                    raise Invalid("scadenza non valida: usa AAAA-MM-GG")
                out[key] = date.isoformat()
            elif key == "owner":
                out[key] = self._link(wiki, value, "person")
            else:  # related
                if not isinstance(value, list):
                    raise Invalid("'related' deve essere una lista di titoli")
                out[key] = [self._link(wiki, v) for v in value]
        return out

    def _link(self, wiki, name, type_name=None):
        target = link_target_name(name) if isinstance(name, str) else None
        pages = wiki.lookup(target)[1] if target else []
        if len(pages) != 1 or (type_name and pages[0].type != type_name):
            kind = f" di tipo '{type_name}'" if type_name else ""
            raise Invalid(f"nessuna pagina{kind} con titolo '{name}'")
        return f"[[{pages[0].stem}]]"

    def _error_keys(self, wiki, rel):
        return {(i.code, i.message) for i in validate(wiki, [rel]) if i.severity == "error"}

    def _new_errors(self, rel, before):
        wiki = self.refresh()
        return [i.to_dict() for i in validate(wiki, [rel])
                if i.severity == "error" and (i.code, i.message) not in before]

    def _backup(self):
        files = {}
        for root_name in PAGE_ROOTS:
            base = self.root / root_name
            if base.is_dir():
                for path in base.rglob("*.md"):
                    files[path.relative_to(self.root).as_posix()] = path.read_bytes()
        return files

    def _restore(self, backup, full):
        if full:
            for rel in set(self._backup()) - set(backup):
                (self.root / rel).unlink()
        for rel, data in backup.items():
            path = self.root / rel
            if not path.exists() or path.read_bytes() != data:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        self.refresh()

    def _summary(self, title, fields, note, new_title):
        parts = [f"{k}={_describe(v)}" for k, v in fields.items()]
        if new_title:
            parts.append(f"titolo={new_title}")
        if note:
            parts.append("nota")
        return f"{title} → " + ", ".join(parts)

    def _close(self, paths, summary):
        wiki = self.refresh()
        write_index(wiki)
        append_log(self.root, summary, op="board")
        if not self.git.is_repo():
            return False
        own = set(paths) | {"index.md", "log.md"}
        ok, error = self.git.commit(sorted(own | self.pending_commit), f"sb(board): {summary}")
        if not ok and self.pending_commit - own:
            # un file in sospeso non deve bloccare i commit successivi: riprova con i soli file di ora
            ok, error = self.git.commit(sorted(own), f"sb(board): {summary}")
            if ok:
                self.last_commit_error = error
                self.pusher.mark()
                return True
        if ok:
            self.pending_commit.clear()
            self.last_commit_error = None
            self.pusher.mark()
        else:
            self.pending_commit |= set(paths)
            self.last_commit_error = error
        return ok
