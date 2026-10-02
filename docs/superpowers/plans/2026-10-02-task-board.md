# Task Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere al plugin `sb` una board web locale per i task: server HTTP in standard library, UI in un solo file HTML/JS e skill `/sb:board`. Ogni modifica passa dal toolkit, con validazione, log e commit.

**Architecture:**
- `board_api.py` contiene la logica pura: snapshot, create, update.
- `board_server.py` è un adattatore HTTP sottile, con token, controllo dell'Host e lock.
- `gitops.py` fa commit selettivi e push raggruppato.
- `frontmatter.update_text` modifica solo i campi toccati.
- La UI (`toolkit/board/index.html`) parla solo JSON.
- I comandi `sb tasks add` e `sb tasks update` riusano `board_api`.

**Tech Stack:** Python ≥ 3.9 solo standard library (`http.server`, `threading`, `subprocess`, `unittest`); HTML/CSS/JS vanilla senza build; git.

**Spec:** `docs/superpowers/specs/2026-10-02-task-board-design.md` (dipende da `docs/superpowers/specs/2026-10-02-second-brain-core-design.md`)

## Global Constraints

- Python ≥ 3.9, solo standard library; nessuna dipendenza JS, nessuna build.
- Server solo su `127.0.0.1`. Ogni `/api/*` richiede `X-SB-Token`; ogni richiesta richiede `Host` uguale a `127.0.0.1:<porta>` o `localhost:<porta>`.
- Porta di default 8765, con tentativi fino a 10 porte successive.
- Path della wiki: `--wiki`, poi `SB_WIKI`, poi la cartella corrente o una sua cartella madre.
- Polling della UI ogni 5 s su `/api/version`. Push al massimo ogni 60 s, più uno all'arresto.
- Commit con messaggio `sb(board): <titolo> → <modifica>` dei soli file toccati più `index.md` e `log.md`; mai `git add -A`.
- Codici di risposta: `403` token o Host non validi, `404` task inesistente, `409` conflitto o duplicato, `422` valore non valido o validazione fallita, `500` errore inatteso.
- Note: `- AAAA-MM-GG: <testo>`, su una riga sola.
- Palette della UI:
  - fondo `#F2ECE3`, barra `#F6F1EA`, card `#FBF8F3`, bordo `#E0D5C5`;
  - testo `#2A231D` e `#66594D`, accento `#A2461E`;
  - colonne `sand #ECE4D8`, `ochre #EFE3CC`, `clay #F1DED4`, `sage #E5E5D4`, `stone #E8E3DB`.
- Font della UI: Instrument Sans 12px e IBM Plex Mono.
- Testi rivolti all'utente in italiano.
- Test: `python3 -m unittest discover -s tests -v` dalla radice del repo.

## Review Focus

1. **Titoli con accenti e spazi** (`Riunione con Nicolò`): creazione e modifica funzionano, perché il percorso viaggia nel corpo JSON e non nell'URL. Test in Task 5.
2. **Lo stesso task modificato da Claude Code mentre la board è aperta**: la modifica dalla board con un etag vecchio dà `409` e non sovrascrive. Test in Task 5 e Task 7.
3. **Wiki senza git, oppure senza remote**: la board scrive e valida, `committed: false`, nessun crash, push saltato. Test in Task 3 e Task 5.
4. **Nota con a capo o spazi multipli** incollata dalla UI: diventa una sola riga `- data: testo`. Test in Task 5.
5. **`.sb/board.json` rimasto da un processo morto**: `sb board` lo ignora e avvia un server nuovo. Test in Task 7.

---

## File Structure

```
toolkit/sb_core/cli.py          # SB_WIKI, payload d'errore, tasks add/update, board      (Task 1, 6, 7)
toolkit/sb_core/frontmatter.py  # + update_text                                            (Task 2)
toolkit/sb_core/gitops.py       # Git (commit selettivo, push), PushScheduler              (Task 3)
toolkit/sb_core/board_api.py    # Board: snapshot, version, create, update                (Task 4, 5)
toolkit/sb_core/board_server.py # bind, start, run, handler HTTP                          (Task 7)
toolkit/board/index.html        # UI                                                      (Task 8)
skills/board/SKILL.md           # /sb:board [stop|status]                                 (Task 9)
skills/tasks/SKILL.md           # azioni via sb tasks add/update                          (Task 9)
references/conventions.md       # tabella comandi                                         (Task 9)
README.md, tests/scenarios/board.md                                                         (Task 9)
tests/helpers.py                # + make_git_wiki, add_bare_remote, git()                 (Task 3)
tests/test_env.py, test_update_text.py, test_gitops.py, test_board_api.py,
tests/test_board_cli.py, test_board_server.py, test_board_ui.py
```

---
### Task 1: `SB_WIKI` e payload d'errore nella CLI

**Files:**
- Modify: `toolkit/sb_core/cli.py`
- Test: `tests/test_env.py`

**Interfaces:**
- Produces:
  - `cli._wiki_path(args) -> str`: `args.wiki`, altrimenti `os.environ["SB_WIKI"]`, altrimenti `"."`. Lo usano `_wiki` e `cmd_version`.
  - `main` emette `exc.payload`, quando l'eccezione `SbError` ne ha uno, al posto di `{"error": str(exc)}`. Serve alle risposte di `BoardError` (Task 4).
  - L'opzione comune `--wiki` passa a `default=None`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_env.py`:

```python
import os
import unittest
from unittest import mock

from helpers import WikiCase, run_cli
from sb_core import cli
from sb_core.errors import SbError


class WikiEnvTest(WikiCase):
    def test_sb_wiki_is_used_without_flag(self):
        root = self.make_wiki()
        with mock.patch.dict(os.environ, {"SB_WIKI": str(root)}):
            code, data, _ = run_cli("version")
        self.assertEqual((code, data["wiki"]), (0, str(root.resolve())))

    def test_flag_wins_over_env(self):
        first, second = self.make_wiki(), self.make_wiki()
        with mock.patch.dict(os.environ, {"SB_WIKI": str(first)}):
            code, data, _ = run_cli("version", "--wiki", second)
        self.assertEqual(data["wiki"], str(second.resolve()))

    def test_env_is_used_by_wiki_commands(self):
        root = self.make_wiki()
        with mock.patch.dict(os.environ, {"SB_WIKI": str(root)}):
            code, data, _ = run_cli("validate")
        self.assertEqual((code, data["ok"]), (0, True))

    def test_error_payload_is_emitted(self):
        class WithPayload(SbError):
            payload = {"error": "doppione", "path": "operations/tasks/X.md"}

        with mock.patch.object(cli, "cmd_version", side_effect=WithPayload("doppione")):
            code, data, _ = run_cli("version")
        self.assertEqual((code, data), (2, {"error": "doppione", "path": "operations/tasks/X.md"}))


if __name__ == "__main__":
    unittest.main()
```

Nota: `test_error_payload_is_emitted` sostituisce `cli.cmd_version` con `mock.patch.object`. Per questo l'handler registrato da `_add_version` deve cercare `cmd_version` nel modulo al momento della chiamata, con una lambda (Step 3, punto 5), invece di tenere un riferimento fisso alla funzione.

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_env.py' -v`
Expected: FAIL su `test_sb_wiki_is_used_without_flag` (`wiki` è `None`), su `test_env_is_used_by_wiki_commands` (exit 2) e su `test_error_payload_is_emitted` (payload diverso)

- [ ] **Step 3: Implementa**

In `toolkit/sb_core/cli.py`:

1. aggiungi `import os` agli import della standard library;
2. nella funzione `main` sostituisci il ramo `except SbError as exc:` con:

```python
    except SbError as exc:
        print(f"sb: {exc}", file=sys.stderr)
        _emit(getattr(exc, "payload", None) or {"error": str(exc)})
        return 2
```

3. in `build_parser` cambia l'opzione comune:

```python
    common.add_argument("--wiki", default=None,
                        help="cartella della wiki o una sua sottocartella (default: $SB_WIKI, poi .)")
```

4. sostituisci `cmd_version` e `_wiki` con:

```python
def _wiki_path(args):
    return getattr(args, "wiki", None) or os.environ.get("SB_WIKI") or "."


def cmd_version(args):
    try:
        root = str(find_root(_wiki_path(args)))
    except SbError:
        root = None
    return {"toolkit": __version__, "format": FORMAT_VERSION, "wiki": root}, 0


def _wiki(args):
    return Wiki(_wiki_path(args))
```

5. in `_add_version` fai in modo che l'handler venga letto dal modulo al momento della chiamata:

```python
def _add_version(sub, common):
    p = sub.add_parser("version", parents=[common], help="versione del toolkit e wiki corrente")
    p.set_defaults(handler=lambda args: cmd_version(args))
```

- [ ] **Step 4: Esegui tutti i test**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core/cli.py tests/test_env.py
git commit -m "feat(toolkit): SB_WIKI env var and structured error payloads"
```

---

### Task 2: `frontmatter.update_text`

**Files:**
- Modify: `toolkit/sb_core/frontmatter.py`
- Test: `tests/test_update_text.py`

**Interfaces:**
- Consumes: `frontmatter.split`, `frontmatter.dump`, `frontmatter.render`, `frontmatter._is_item`.
- Produces: `frontmatter.update_text(text, changes) -> str`.
  - `changes` è un `dict`; `None` rimuove il campo.
  - Ogni campo presente viene sostituito nel suo intervallo di righe (riga chiave più righe indentate o di lista).
  - I campi nuovi vengono aggiunti prima della chiusura del frontmatter.
  - Tutte le altre righe, commenti compresi, restano identiche.
  - Senza frontmatter ne viene creato uno, con i soli campi non `None`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_update_text.py`:

```python
import unittest

import helpers  # noqa: F401
from sb_core.frontmatter import parse, update_text

SRC = (
    "---\n"
    "# commento dell'utente\n"
    "type: task\n"
    "title: Stima   # titolo\n"
    "related:\n"
    '  - "[[A]]"\n'
    '  - "[[B]]"\n'
    "priority: low\n"
    "---\n"
    "Corpo\n"
)


class UpdateTextTest(unittest.TestCase):
    def test_replaces_only_the_changed_line(self):
        out = update_text(SRC, {"priority": "high"})
        self.assertEqual(out, SRC.replace("priority: low", "priority: high"))

    def test_replaces_a_whole_block(self):
        out = update_text(SRC, {"related": ["[[C]]"]})
        self.assertEqual(out, SRC.replace('related:\n  - "[[A]]"\n  - "[[B]]"\n', 'related: ["[[C]]"]\n'))
        self.assertIn("# commento dell'utente", out)

    def test_removes_with_none(self):
        out = update_text(SRC, {"priority": None})
        self.assertNotIn("priority", out)
        self.assertEqual(parse(out)[0]["title"], "Stima")

    def test_appends_new_fields_before_closing(self):
        out = update_text(SRC, {"due": "2026-10-09", "owner": "[[Luca Bianchi]]"})
        self.assertTrue(out.endswith('priority: low\ndue: 2026-10-09\nowner: "[[Luca Bianchi]]"\n---\nCorpo\n'))

    def test_multiple_changes_and_round_trip(self):
        out = update_text(SRC, {"priority": None, "related": None, "status": "done"})
        meta, body = parse(out)
        self.assertEqual(meta, {"type": "task", "title": "Stima", "status": "done"})
        self.assertEqual(body, "Corpo\n")

    def test_without_frontmatter(self):
        self.assertEqual(update_text("Corpo\n", {"type": "task", "x": None}), "---\ntype: task\n---\nCorpo\n")
        self.assertEqual(update_text("Corpo\n", {"x": None}), "Corpo\n")

    def test_empty_frontmatter(self):
        self.assertEqual(update_text("---\n---\nx", {"a": 1}), "---\na: 1\n---\nx")

    def test_crlf_input_is_normalised(self):
        out = update_text("---\r\ntitle: T\r\n---\r\nCorpo\r\n", {"title": "U"})
        self.assertEqual(out, "---\ntitle: U\n---\nCorpo\n")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_update_text.py' -v`
Expected: ERROR `ImportError: cannot import name 'update_text'`

- [ ] **Step 3: Implementa**

Aggiungi in fondo a `toolkit/sb_core/frontmatter.py`:

```python
_KEY_LINE = re.compile(r"^([^\s#:-][^:]*):")


def update_text(text, changes):
    """Modifica solo i campi indicati del frontmatter (None li rimuove); il resto resta identico."""
    fm, body = split(text)
    if fm is None:
        fresh = {k: v for k, v in changes.items() if v is not None}
        return render(fresh, body) if fresh else body
    lines = fm.split("\n") if fm else []
    for key, value in changes.items():
        new_lines = [] if value is None else dump({key: value}).rstrip("\n").split("\n")
        spans = _key_spans(lines)
        if key in spans:
            start, end = spans[key]
            lines[start:end] = new_lines
        elif value is not None:
            insert_at = len(lines)
            while insert_at > 0 and not lines[insert_at - 1].strip():
                insert_at -= 1
            lines[insert_at:insert_at] = new_lines
    inner = "\n".join(lines) + "\n" if lines else ""
    return "---\n" + inner + "---\n" + body


def _key_spans(lines):
    """Per ogni chiave di primo livello: (prima riga, riga dopo l'ultima) del suo valore."""
    spans = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        match = None
        if line and line[0] not in " \t#" and not _is_item(line):
            match = _KEY_LINE.match(line)
        if not match:
            i += 1
            continue
        start = i
        i += 1
        while i < len(lines) and lines[i].strip() and (lines[i][0] in " \t" or _is_item(lines[i])):
            i += 1
        spans[match.group(1).strip()] = (start, i)
    return spans
```

- [ ] **Step 4: Esegui tutti i test**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core/frontmatter.py tests/test_update_text.py
git commit -m "feat(toolkit): surgical frontmatter field updates"
```

---

### Task 3: `gitops`: commit selettivo e push raggruppato

**Files:**
- Create: `toolkit/sb_core/gitops.py`
- Modify: `tests/helpers.py` (aggiunge `git`, `WikiCase.make_git_wiki`, `WikiCase.add_bare_remote`)
- Test: `tests/test_gitops.py`

**Interfaces:**
- Produces:
  - `gitops.Git(root)` con questi metodi:
    - `.is_repo() -> bool`;
    - `.head() -> str | None` (hash corto);
    - `.has_remote() -> bool`;
    - `.commit(paths, message) -> (ok: bool, error: str | None)`: committa solo `paths` (relativi alla radice), comprese le cancellazioni. I path che non esistono e non sono tracciati vengono ignorati; se non c'è nulla da committare ritorna `(True, None)`;
    - `.push() -> (ok, error)`: usa `-u origin HEAD` se manca l'upstream.
  - `gitops.PushScheduler(git, interval=60, clock=time.monotonic)` con questi metodi:
    - `.mark()`;
    - `.tick()`: fa il push solo se c'è qualcosa in sospeso e sono passati almeno `interval` secondi dall'ultimo tentativo;
    - `.flush()`: fa il push se c'è qualcosa in sospeso, a prescindere dall'intervallo;
    - `.state() -> {"pending_push", "last_push", "last_error"}`.

    Senza remote un tentativo azzera lo stato di "in sospeso".
  - Helper di test: `helpers.git(root, *args) -> str`, `WikiCase.make_git_wiki(files=None) -> Path`, `WikiCase.add_bare_remote(root) -> Path`.

- [ ] **Step 1: Estendi gli helper e scrivi i test che falliscono**

Aggiungi in fondo a `tests/helpers.py`:

```python
import subprocess


def git(root, *args):
    """Esegue git nella cartella indicata e ritorna stdout; fallisce se git fallisce."""
    return subprocess.run(["git", *[str(a) for a in args]], cwd=str(root),
                          capture_output=True, text=True, check=True).stdout


def _make_git_wiki(self, files=None):
    root = self.make_wiki(files)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    return root


def _add_bare_remote(self, root):
    remote = Path(tempfile.mkdtemp(prefix="sb-remote-"))
    self.addCleanup(shutil.rmtree, str(remote), True)
    git(remote, "init", "-q", "--bare")
    git(root, "remote", "add", "origin", remote)
    return remote


WikiCase.make_git_wiki = _make_git_wiki
WikiCase.add_bare_remote = _add_bare_remote
```

`tests/test_gitops.py`:

```python
import os
import unittest

from helpers import WikiCase, git, md
from sb_core.gitops import Git, PushScheduler

A = "operations/tasks/A.md"


class GitTest(WikiCase):
    def test_commits_only_the_given_paths(self):
        root = self.make_git_wiki({A: md("type: task\ntitle: A")})
        (root / A).write_text(md("type: task\ntitle: A\nstatus: done"), encoding="utf-8")
        (root / "operations/tasks/B.md").write_text(md("type: task\ntitle: B"), encoding="utf-8")
        (root / "knowledge/topics").mkdir(parents=True)
        (root / "knowledge/topics/Estraneo.md").write_text(md("type: topic\ntitle: Estraneo"), encoding="utf-8")
        ok, error = Git(root).commit([A, "operations/tasks/B.md", "operations/tasks/Mancante.md"], "sb(board): test")
        self.assertEqual((ok, error), (True, None))
        committed = git(root, "show", "--name-only", "--format=", "HEAD").split("\n")
        self.assertEqual(sorted(p for p in committed if p), [A, "operations/tasks/B.md"])
        self.assertIn("knowledge/", git(root, "status", "--porcelain"))
        self.assertEqual(git(root, "log", "-1", "--format=%s").strip(), "sb(board): test")

    def test_commits_deletions(self):
        root = self.make_git_wiki({A: md("type: task\ntitle: A")})
        os.rename(str(root / A), str(root / "operations/tasks/C.md"))
        ok, _ = Git(root).commit([A, "operations/tasks/C.md"], "rename")
        self.assertTrue(ok)
        self.assertEqual(git(root, "status", "--porcelain").strip(), "")

    def test_nothing_to_commit_is_ok(self):
        root = self.make_git_wiki({A: md("type: task\ntitle: A")})
        self.assertEqual(Git(root).commit([A], "noop"), (True, None))
        self.assertEqual(git(root, "log", "-1", "--format=%s").strip(), "init")

    def test_not_a_repo(self):
        repo = Git(self.make_wiki())
        self.assertFalse(repo.is_repo())
        self.assertIsNone(repo.head())
        ok, error = repo.commit(["x.md"], "m")
        self.assertFalse(ok)
        self.assertTrue(error)

    def test_head_and_remote(self):
        root = self.make_git_wiki()
        repo = Git(root)
        self.assertTrue(repo.head())
        self.assertFalse(repo.has_remote())
        self.add_bare_remote(root)
        self.assertTrue(repo.has_remote())


class PushSchedulerTest(WikiCase):
    def test_pushes_at_most_once_per_interval_and_flushes(self):
        root = self.make_git_wiki({A: md("type: task\ntitle: A")})
        remote = self.add_bare_remote(root)
        clock = [100.0]
        pusher = PushScheduler(Git(root), interval=60, clock=lambda: clock[0])
        pusher.tick()
        self.assertFalse(pusher.state()["pending_push"])
        pusher.mark()
        pusher.tick()
        self.assertEqual(git(remote, "rev-parse", "main").strip(), git(root, "rev-parse", "HEAD").strip())
        self.assertFalse(pusher.state()["pending_push"])
        self.assertTrue(pusher.state()["last_push"])

        (root / A).write_text(md("type: task\ntitle: A\nstatus: done"), encoding="utf-8")
        Git(root).commit([A], "seconda")
        pusher.mark()
        clock[0] = 130.0
        pusher.tick()
        self.assertTrue(pusher.state()["pending_push"])
        clock[0] = 161.0
        pusher.tick()
        self.assertFalse(pusher.state()["pending_push"])
        self.assertEqual(git(remote, "rev-parse", "main").strip(), git(root, "rev-parse", "HEAD").strip())

        pusher.mark()
        clock[0] = 162.0
        pusher.flush()
        self.assertFalse(pusher.state()["pending_push"])

    def test_failed_push_stays_pending(self):
        root = self.make_git_wiki()
        git(root, "remote", "add", "origin", "/percorso/che/non/esiste.git")
        pusher = PushScheduler(Git(root), clock=lambda: 0.0)
        pusher.mark()
        pusher.tick()
        state = pusher.state()
        self.assertTrue(state["pending_push"])
        self.assertTrue(state["last_error"])

    def test_without_remote_nothing_stays_pending(self):
        pusher = PushScheduler(Git(self.make_git_wiki()), clock=lambda: 0.0)
        pusher.mark()
        pusher.flush()
        self.assertFalse(pusher.state()["pending_push"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_gitops.py' -v`
Expected: ERROR `No module named 'sb_core.gitops'`

- [ ] **Step 3: Implementa**

`toolkit/sb_core/gitops.py`:

```python
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
```

- [ ] **Step 4: Esegui tutti i test**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core/gitops.py tests/helpers.py tests/test_gitops.py
git commit -m "feat(toolkit): selective git commits and batched push"
```

---
### Task 4: `board_api`: snapshot e version

**Files:**
- Create: `toolkit/sb_core/board_api.py` (solo lettura in questo task)
- Test: `tests/test_board_api.py` (prima parte)

**Interfaces:**
- Consumes: `Wiki`, `wiki.closed_statuses`, `wiki.parse_date`, `tasks.list_tasks`, `tasks.task_record`, `names.norm`, `gitops.Git`, `gitops.PushScheduler`, `errors.SbError`.
- Produces:
  - `board_api.BoardError(message, **payload)`, con `.status` (400) e `.payload` (`dict(payload, error=message)`), e le sottoclassi `NotFound` (404), `Conflict` (409), `Invalid` (422).
  - `board_api.etag_of(data: bytes) -> str` (sha1 esadecimale).
  - `board_api.Board(wiki_path, today=None, push_interval=60)` con:
    - attributi `.root`, `.wiki`, `.git`, `.pusher`, `.lock`, `.pending_commit: set`, `.last_commit_error`;
    - metodi `.today()`, `.refresh() -> Wiki`, `.enums(wiki) -> {"status","priority","closed"}`, `.snapshot() -> dict`, `.version() -> {"version"}`, `.sync_state() -> dict`, `._decorate(wiki, record)`, `._record(rel)`.
  - Il record di un task nello snapshot è il contratto di `tasks list` più `body`, `updated` ed `etag`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_board_api.py`:

```python
import datetime
import os
import unittest
from unittest import mock

from helpers import WikiCase, git, md
from sb_core.board_api import Board, Conflict, Invalid, NotFound, etag_of
from sb_core.frontmatter import parse
from sb_core.validate import Issue

TODAY = datetime.date(2026, 10, 2)
T = "operations/tasks/Stima.md"
FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi\naliases: [Luca]"),
    "knowledge/people/Anna Neri.md": md("type: person\ntitle: Anna Neri"),
    "knowledge/people/Ex Collega.md": md("type: person\ntitle: Ex Collega\nstatus: left"),
    "knowledge/projects/Migrazione DB.md": md("type: project\ntitle: Migrazione DB"),
    "knowledge/topics/On-call.md": md("type: topic\ntitle: On-call", "Vedi [[Stima]].\n"),
    T: md(
        'type: task\ntitle: Stima\n# nota utente\nowner: "[[Luca Bianchi]]"\npriority: low\n'
        'related: ["[[Migrazione DB]]"]\ncreated: 2026-09-15',
        "Contesto.\n",
    ),
    "operations/tasks/Chiuso.md": md("type: task\ntitle: Chiuso\nstatus: done\nupdated: 2026-09-30"),
}


def read(root, rel):
    return (root / rel).read_text(encoding="utf-8")


class SnapshotTest(WikiCase):
    def test_snapshot_shape(self):
        root = self.make_wiki(FILES)
        snap = Board(root, today=lambda: TODAY).snapshot()
        self.assertEqual(set(snap), {"wiki", "today", "thresholds", "enums", "tasks", "people", "projects", "sync"})
        self.assertEqual(snap["wiki"]["name"], root.resolve().name)
        self.assertEqual(snap["today"], "2026-10-02")
        self.assertEqual(snap["thresholds"]["due_soon_days"], 7)
        self.assertEqual(snap["enums"], {
            "status": ["todo", "doing", "blocked", "done", "dropped"],
            "priority": ["low", "medium", "high"],
            "closed": ["done", "dropped"],
        })
        self.assertEqual([p["title"] for p in snap["people"]], ["Anna Neri", "Luca Bianchi"])
        self.assertEqual(snap["projects"], [{"title": "Migrazione DB", "path": "knowledge/projects/Migrazione DB.md"}])
        self.assertFalse(snap["sync"]["git"])

    def test_task_records(self):
        root = self.make_wiki(FILES)
        tasks = {t["title"]: t for t in Board(root, today=lambda: TODAY).snapshot()["tasks"]}
        stima = tasks["Stima"]
        self.assertEqual(stima["owner"], "Luca Bianchi")
        self.assertEqual(stima["related"], ["Migrazione DB"])
        self.assertEqual(stima["body"], "Contesto.\n")
        self.assertEqual(stima["etag"], etag_of((root / T).read_bytes()))
        self.assertIsNone(stima["updated"])
        self.assertEqual(tasks["Chiuso"]["updated"], "2026-09-30")

    def test_sync_state_in_git_wiki(self):
        root = self.make_git_wiki(FILES)
        sync = Board(root).snapshot()["sync"]
        self.assertTrue(sync["git"])
        self.assertEqual(sync["head"], git(root, "rev-parse", "--short", "HEAD").strip())
        self.assertEqual((sync["pending_push"], sync["uncommitted"]), (False, []))

    def test_version_changes_when_a_task_changes(self):
        root = self.make_wiki(FILES)
        board = Board(root)
        before = board.version()["version"]
        self.assertEqual(board.version()["version"], before)
        stat = (root / T).stat()
        os.utime(str(root / T), ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
        self.assertNotEqual(board.version()["version"], before)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_board_api.py' -v`
Expected: ERROR `No module named 'sb_core.board_api'`

- [ ] **Step 3: Implementa la parte di lettura**

`toolkit/sb_core/board_api.py`:

```python
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
```

- [ ] **Step 4: Esegui tutti i test**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`. Gli import di `Conflict`, `Invalid`, `NotFound`, `Issue`, `mock` e `parse` nel test servono al Task 5 e qui restano inutilizzati.

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core/board_api.py tests/test_board_api.py
git commit -m "feat(board): task snapshot and change detection"
```

---

### Task 5: `board_api`: create e update

**Files:**
- Modify: `toolkit/sb_core/board_api.py`
- Test: `tests/test_board_api.py` (aggiunge `UpdateTest` e `CreateTest`)

**Interfaces:**
- Consumes: Task 2 `update_text`, Task 3 `Git.commit` e `PushScheduler.mark`, `frontmatter.render`, `index.write_index`, `log.append_log`, `migrate.migrate`, `links.link_target_name`, `names.title_problem`, `validate.validate`, `errors.PlanError`, `wiki.PAGE_ROOTS`.
- Produces:
  - `Board.create(data) -> {"task", "committed"}`. `data` contiene `title` e, opzionali, `status`, `owner`, `due`, `priority`, `related`, `note`.
  - `Board.update(data) -> {"task", "committed"}`. `data` contiene `path`, `etag` (opzionale; `None` salta il controllo), `set` e `note`.
  - Eccezioni: `NotFound` se il task non esiste; `Conflict` con payload `task` (etag) o `path` (duplicato); `Invalid` con payload `issues` quando la validazione fallisce.
  - Costanti `EDITABLE = ("title", "status", "owner", "due", "priority", "related")` e `FIELD_ORDER = ("status", "owner", "due", "priority", "related")`.

- [ ] **Step 1: Scrivi i test che falliscono**

Aggiungi a `tests/test_board_api.py`, prima di `if __name__`:

```python
class UpdateTest(WikiCase):
    def setUp(self):
        self.root = self.make_git_wiki(FILES)
        self.board = Board(self.root, today=lambda: TODAY)

    def etag(self, rel=T):
        return etag_of((self.root / rel).read_bytes())

    def committed_files(self):
        return sorted(p for p in git(self.root, "show", "--name-only", "--format=", "HEAD").split("\n") if p)

    def test_updates_fields_surgically_and_commits_only_touched_files(self):
        (self.root / "knowledge/topics/Estraneo.md").write_text(md("type: topic\ntitle: Estraneo"), encoding="utf-8")
        result = self.board.update({"path": T, "etag": self.etag(),
                                    "set": {"priority": "high", "due": "2026-10-09", "owner": "Anna Neri"}})
        text = read(self.root, T)
        for fragment in ("# nota utente", "priority: high", 'owner: "[[Anna Neri]]"', "due: 2026-10-09",
                         "updated: 2026-10-02", 'related: ["[[Migrazione DB]]"]', "Contesto.\n"):
            self.assertIn(fragment, text)
        self.assertTrue(result["committed"])
        self.assertEqual(result["task"]["owner"], "Anna Neri")
        self.assertEqual(result["task"]["etag"], self.etag())
        self.assertEqual(self.committed_files(), sorted([T, "index.md", "log.md"]))
        self.assertTrue(git(self.root, "log", "-1", "--format=%s").startswith("sb(board): Stima → "))
        self.assertIn("Estraneo.md", git(self.root, "status", "--porcelain"))
        self.assertTrue(self.board.pusher.state()["pending_push"])

    def test_null_removes_a_field(self):
        self.board.update({"path": T, "etag": self.etag(), "set": {"priority": None, "owner": None}})
        meta, _ = parse(read(self.root, T))
        self.assertNotIn("priority", meta)
        self.assertNotIn("owner", meta)

    def test_note_is_one_dated_line(self):
        self.board.update({"path": T, "etag": self.etag(), "note": "sollecitato\n  in   standup"})
        self.assertTrue(read(self.root, T).endswith("Contesto.\n- 2026-10-02: sollecitato in standup\n"))

    def test_stale_etag_is_a_conflict(self):
        before = (self.root / T).read_bytes()
        with self.assertRaises(Conflict) as ctx:
            self.board.update({"path": T, "etag": "vecchio", "set": {"priority": "high"}})
        self.assertEqual(ctx.exception.payload["task"]["path"], T)
        self.assertEqual((self.root / T).read_bytes(), before)

    def test_invalid_values_write_nothing(self):
        before = (self.root / T).read_bytes()
        for changes in ({"status": "wip"}, {"priority": "urgent"}, {"due": "venerdì"}, {"owner": "Nessuno"},
                        {"owner": "Migrazione DB"}, {"related": "Migrazione DB"}, {"related": ["Fantasma"]},
                        {"type": "risk"}, {}):
            with self.subTest(changes=changes):
                with self.assertRaises(Invalid):
                    self.board.update({"path": T, "etag": self.etag(), "set": changes})
                self.assertEqual((self.root / T).read_bytes(), before)

    def test_unknown_task_is_not_found(self):
        with self.assertRaises(NotFound):
            self.board.update({"path": "operations/tasks/Nessuno.md", "set": {"priority": "high"}})

    def test_retitle_rewrites_links_and_commits_the_rename(self):
        result = self.board.update({"path": T, "etag": self.etag(), "set": {"title": "Stima migrazione DB"}})
        new = "operations/tasks/Stima migrazione DB.md"
        self.assertEqual(result["task"]["path"], new)
        self.assertFalse((self.root / T).exists())
        self.assertIn("[[Stima migrazione DB]]", read(self.root, "knowledge/topics/On-call.md"))
        self.assertEqual(self.committed_files(), sorted([T, new, "knowledge/topics/On-call.md", "index.md", "log.md"]))

    def test_validation_failure_restores_the_file(self):
        before = (self.root / T).read_bytes()
        fake = Issue(T, "bad-value", "errore finto")
        with mock.patch("sb_core.board_api.validate", side_effect=[[], [fake]]):
            with self.assertRaises(Invalid) as ctx:
                self.board.update({"path": T, "etag": self.etag(), "set": {"priority": "high"}})
        self.assertEqual(ctx.exception.payload["issues"][0]["message"], "errore finto")
        self.assertEqual((self.root / T).read_bytes(), before)

    def test_failed_commit_is_retried_with_the_next_change(self):
        with mock.patch.object(self.board.git, "commit", side_effect=[(False, "hook"), (True, None)]) as commit:
            first = self.board.update({"path": T, "etag": self.etag(), "set": {"priority": "high"}})
            self.assertFalse(first["committed"])
            self.assertEqual(self.board.pending_commit, {T})
            self.assertEqual(self.board.sync_state()["commit_error"], "hook")
            self.board.update({"path": "operations/tasks/Chiuso.md",
                               "etag": self.etag("operations/tasks/Chiuso.md"), "set": {"status": "todo"}})
        self.assertIn(T, commit.call_args_list[1][0][0])
        self.assertEqual(self.board.pending_commit, set())

    def test_works_without_git(self):
        root = self.make_wiki(FILES)
        board = Board(root, today=lambda: TODAY)
        result = board.update({"path": T, "etag": etag_of((root / T).read_bytes()), "set": {"status": "doing"}})
        self.assertEqual((result["committed"], result["task"]["status"]), (False, "doing"))
        self.assertEqual(board.pending_commit, set())


class CreateTest(WikiCase):
    def setUp(self):
        self.root = self.make_git_wiki(FILES)
        self.board = Board(self.root, today=lambda: TODAY)

    def test_create_with_all_fields(self):
        result = self.board.create({"title": "Riunione con Nicolò", "status": "doing", "priority": "high",
                                    "owner": "Luca", "related": ["Migrazione DB"], "due": "2026-10-10",
                                    "note": "dalla board"})
        rel = "operations/tasks/Riunione con Nicolò.md"
        meta, body = parse(read(self.root, rel))
        self.assertEqual(list(meta), ["type", "title", "status", "owner", "due", "priority", "related", "created"])
        self.assertEqual(meta["owner"], "[[Luca Bianchi]]")
        self.assertEqual(body, "- 2026-10-02: dalla board\n")
        self.assertEqual((result["committed"], result["task"]["path"]), (True, rel))

    def test_create_with_title_only(self):
        self.board.create({"title": "Solo titolo"})
        meta, body = parse(read(self.root, "operations/tasks/Solo titolo.md"))
        self.assertEqual((meta, body), ({"type": "task", "title": "Solo titolo", "created": "2026-10-02"}, ""))

    def test_invalid_title_and_values(self):
        for data in ({"title": "1:1 Luca"}, {"title": "  "}, {"title": "Ok", "owner": "Nessuno"},
                     {"title": "Ok", "status": "wip"}):
            with self.subTest(data=data):
                with self.assertRaises(Invalid):
                    self.board.create(data)
        self.assertFalse((self.root / "operations/tasks/Ok.md").exists())

    def test_duplicate_title_is_a_conflict(self):
        with self.assertRaises(Conflict) as ctx:
            self.board.create({"title": "stima"})
        self.assertEqual(ctx.exception.payload["path"], T)

    def test_validation_failure_removes_the_new_file(self):
        fake = Issue("x", "bad-value", "errore finto")
        with mock.patch("sb_core.board_api.validate", return_value=[fake]):
            with self.assertRaises(Invalid):
                self.board.create({"title": "Da buttare"})
        self.assertFalse((self.root / "operations/tasks/Da buttare.md").exists())
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_board_api.py' -v`
Expected: ERROR in `UpdateTest` e `CreateTest`: `AttributeError: 'Board' object has no attribute 'update'` / `'create'`

- [ ] **Step 3: Implementa la scrittura**

In `toolkit/sb_core/board_api.py`:

1. sostituisci il blocco degli import interni con:

```python
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
```

2. aggiungi dopo `DEFAULT_PRIORITY`:

```python
EDITABLE = ("title", "status", "owner", "due", "priority", "related")
FIELD_ORDER = ("status", "owner", "due", "priority", "related")
```

3. aggiungi dopo `_iso`:

```python
def _describe(value):
    if value is None:
        return "∅"
    if isinstance(value, list):
        return ", ".join(link_target_name(v) or v for v in value) or "∅"
    return link_target_name(value) or str(value)


def _one_line(text):
    return " ".join(str(text or "").split())
```

4. aggiungi in fondo alla classe `Board`:

```python
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
                if date is None:
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
        files = sorted(set(paths) | self.pending_commit | {"index.md", "log.md"})
        ok, error = self.git.commit(files, f"sb(board): {summary}")
        if ok:
            self.pending_commit.clear()
            self.last_commit_error = None
            self.pusher.mark()
        else:
            self.pending_commit |= set(paths)
            self.last_commit_error = error
        return ok
```

- [ ] **Step 4: Esegui tutti i test**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core/board_api.py tests/test_board_api.py
git commit -m "feat(board): deterministic task create and update with rollback"
```

---

### Task 6: comandi `sb tasks add` e `sb tasks update`

**Files:**
- Modify: `toolkit/sb_core/cli.py`
- Test: `tests/test_board_cli.py`

**Interfaces:**
- Consumes: `board_api.Board` (`create`, `update`), `validate._relative`, `cli._wiki_path`, `cli._today`.
- Produces:
  - **`sb tasks add`** `--title T [--status S] [--owner P] [--due D] [--priority X] [--related R]… [--note N]` → `{"task", "committed", "pushed"}`.
  - **`sb tasks update`** `<path> [--set campo=valore]… [--unset campo]… [--note N] [--etag E]` → stessa risposta. In `--set related=A,B` la virgola separa i titoli.
  - `pushed` vale `true`/`false` dopo un push immediato quando esiste un remote e il commit è riuscito; altrimenti `null`.
  - Errori della board → exit 2, con il loro payload come JSON.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_board_cli.py`:

```python
import unittest

from helpers import WikiCase, git, md, run_cli

FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi"),
    "knowledge/projects/Migrazione DB.md": md("type: project\ntitle: Migrazione DB"),
}


class TasksWriteCliTest(WikiCase):
    def test_add_then_update(self):
        root = self.make_git_wiki(FILES)
        code, data, _ = run_cli("tasks", "add", "--title", "Chiamare Luca", "--owner", "Luca Bianchi",
                                "--due", "2026-10-09", "--related", "Migrazione DB", "--related", "Luca Bianchi",
                                "--wiki", root, "--today", "2026-10-02")
        self.assertEqual(code, 0, data)
        self.assertEqual((data["task"]["owner"], data["committed"], data["pushed"]), ("Luca Bianchi", True, None))
        self.assertEqual(data["task"]["related"], ["Migrazione DB", "Luca Bianchi"])
        path = data["task"]["path"]

        code, data, _ = run_cli("tasks", "update", path, "--set", "priority=high", "--unset", "due",
                                "--set", "related=Migrazione DB", "--note", "fatto il punto",
                                "--wiki", root, "--today", "2026-10-02")
        self.assertEqual(code, 0, data)
        self.assertEqual((data["task"]["priority"], data["task"]["due"], data["task"]["related"]),
                         ("high", None, ["Migrazione DB"]))
        self.assertTrue(git(root, "log", "-1", "--format=%s").startswith("sb(board): Chiamare Luca → "))

    def test_errors_carry_their_payload(self):
        root = self.make_git_wiki(FILES)
        run_cli("tasks", "add", "--title", "Chiamare Luca", "--wiki", root)
        code, data, _ = run_cli("tasks", "add", "--title", "Chiamare Luca", "--wiki", root)
        self.assertEqual((code, data["path"]), (2, "operations/tasks/Chiamare Luca.md"))
        code, data, _ = run_cli("tasks", "update", "operations/tasks/Chiamare Luca.md", "--set", "status=wip",
                                "--wiki", root)
        self.assertEqual(code, 2)
        self.assertIn("stato non ammesso", data["error"])
        code, data, _ = run_cli("tasks", "update", "operations/tasks/Chiamare Luca.md", "--set", "priority",
                                "--wiki", root)
        self.assertEqual(code, 2)

    def test_add_pushes_when_a_remote_exists(self):
        root = self.make_git_wiki(FILES)
        remote = self.add_bare_remote(root)
        code, data, _ = run_cli("tasks", "add", "--title", "Con push", "--wiki", root)
        self.assertEqual((code, data["pushed"]), (0, True))
        self.assertEqual(git(remote, "rev-parse", "main").strip(), git(root, "rev-parse", "HEAD").strip())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_board_cli.py' -v`
Expected: FAIL/ERROR: `argument <azione>: invalid choice: 'add'` (exit 2 senza JSON)

- [ ] **Step 3: Implementa**

In `toolkit/sb_core/cli.py` aggiungi gli import `from .board_api import Board` e `from .validate import _relative`. Poi, dentro `_add_tasks`, dopo il blocco di `list`:

```python
    ap = tsub.add_parser("add", parents=[common], help="crea un task con campi espliciti")
    ap.add_argument("--title", required=True)
    ap.add_argument("--status")
    ap.add_argument("--owner", help="titolo di una pagina person")
    ap.add_argument("--due", help="AAAA-MM-GG")
    ap.add_argument("--priority")
    ap.add_argument("--related", action="append", default=[], help="titolo collegato (ripetibile)")
    ap.add_argument("--note")
    ap.set_defaults(handler=cmd_tasks_add)

    up = tsub.add_parser("update", parents=[common], help="modifica un task")
    up.add_argument("path", help="percorso del task")
    up.add_argument("--set", dest="sets", action="append", default=[], metavar="CAMPO=VALORE")
    up.add_argument("--unset", action="append", default=[], metavar="CAMPO")
    up.add_argument("--note")
    up.add_argument("--etag", help="rifiuta la modifica se il file è cambiato")
    up.set_defaults(handler=cmd_tasks_update)
```

e prima di `COMMANDS`:

```python
def _board(args):
    today = _today(args) if getattr(args, "today", None) else None
    return Board(_wiki_path(args), today=(lambda: today) if today else None)


def _with_push(board, result):
    pushed = None
    if result["committed"] and board.git.has_remote():
        pushed, _ = board.git.push()
    return dict(result, pushed=pushed)


def cmd_tasks_add(args):
    board = _board(args)
    data = {"title": args.title, "status": args.status, "owner": args.owner, "due": args.due,
            "priority": args.priority, "related": args.related, "note": args.note}
    return _with_push(board, board.create(data)), 0


def cmd_tasks_update(args):
    board = _board(args)
    changes = {}
    for item in args.sets:
        key, sep, value = item.partition("=")
        if not sep or not key.strip():
            raise UsageError(f"--set vuole CAMPO=VALORE, non '{item}'")
        key = key.strip()
        changes[key] = [v.strip() for v in value.split(",") if v.strip()] if key == "related" else value.strip()
    for key in args.unset:
        changes[key.strip()] = None
    rel = _relative(board.wiki, args.path)
    result = board.update({"path": rel, "etag": args.etag, "set": changes, "note": args.note})
    return _with_push(board, result), 0
```

- [ ] **Step 4: Esegui tutti i test**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core/cli.py tests/test_board_cli.py
git commit -m "feat(toolkit): sb tasks add / update commands"
```

---
### Task 7: `board_server` e comando `sb board`

**Files:**
- Create: `toolkit/sb_core/board_server.py`
- Create: `toolkit/board/index.html` (segnaposto minimo; la UI completa arriva nel Task 8)
- Modify: `toolkit/sb_core/cli.py` (comando `board`)
- Test: `tests/test_board_server.py`

**Interfaces:**
- Consumes: `board_api.Board` (`snapshot`, `version`, `create`, `update`, `pusher`, `root`), `board_api.BoardError`, `errors.SbError`, `errors.WikiError`.
- Produces:
  - `board_server.HTML_PATH`, `board_server.STATE_FILE = ".sb/board.json"`.
  - `board_server.bind(port, attempts=10) -> ThreadingHTTPServer`: porta 0 = effimera; se nessuna porta è libera solleva `WikiError`.
  - `board_server.start(board, port=8765, token=None) -> server`, con `server.app.token` e `server.app.board`.
  - `board_server.url_of(server) -> "http://127.0.0.1:<port>/?t=<token>"`.
  - `board_server.running_board(root) -> dict | None`: le informazioni di `.sb/board.json` se il `pid` è vivo.
  - `board_server.run(board, port, open_browser, emit) -> dict`: stampa le informazioni d'avvio con `emit(dict)`, serve fino a SIGTERM/SIGINT, fa `pusher.flush()` e rimuove il file di stato.
  - CLI `sb board [--port N] [--no-open]`: prima riga di stdout = JSON compatto `{pid, port, url, started}`, oppure `{already_running: true, …}`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_board_server.py`:

```python
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
from sb_core.board_server import STATE_FILE, running_board, start

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
        status, data = self.call("POST", "/api/tasks", {"title": "Nuovo", "status": "doing"})
        self.assertEqual((status, data["task"]["status"]), (201, "doing"))
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

    def test_stale_state_file_is_ignored(self):
        root = self.make_wiki(FILES)
        (root / ".sb").mkdir(exist_ok=True)
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        (root / STATE_FILE).write_text(json.dumps({"pid": dead.pid, "url": "http://vecchio"}), encoding="utf-8")
        self.assertIsNone(running_board(root))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_board_server.py' -v`
Expected: ERROR `No module named 'sb_core.board_server'`

- [ ] **Step 3: Implementa**

`toolkit/board/index.html` (segnaposto, sostituito nel Task 8):

```html
<!doctype html>
<html lang="it"><head><meta charset="utf-8"><title>Board</title></head><body>Board</body></html>
```

`toolkit/sb_core/board_server.py`:

```python
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
```

In `toolkit/sb_core/cli.py` aggiungi `from .board_server import run as run_board` e, prima di `COMMANDS`:

```python
def _add_board(sub, common):
    p = sub.add_parser("board", parents=[common], help="avvia la board dei task nel browser")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-open", action="store_true", help="non aprire il browser")
    p.set_defaults(handler=cmd_board)


def cmd_board(args):
    board = _board(args)
    return run_board(board, port=args.port, open_browser=not args.no_open), 0
```

Aggiungi `_add_board` in coda alla lista `COMMANDS`.

- [ ] **Step 4: Esegui tutti i test**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Smoke test con curl**

Run:

```bash
W=$(mktemp -d)/w && python3 toolkit/sb.py scaffold presets/head-of-engineering "$W" >/dev/null \
 && (python3 toolkit/sb.py board --no-open --port 0 --wiki "$W" > "$W.out" &) && sleep 1 \
 && URL=$(head -1 "$W.out" | python3 -c 'import json,sys;print(json.load(sys.stdin)["url"])') \
 && T=${URL#*?t=} && P=$(echo "$URL" | sed -E 's#.*:([0-9]+)/.*#\1#') \
 && curl -s -H "X-SB-Token: $T" "http://127.0.0.1:$P/api/snapshot" | head -c 300; echo \
 && curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:$P/api/snapshot" \
 && kill $(python3 -c "import json;print(json.load(open('$W/.sb/board.json'))['pid'])")
```

Expected: il JSON dello snapshot (con `"tasks": []`), poi `403`, poi il processo termina.

- [ ] **Step 6: Commit**

```bash
git add toolkit/sb_core/board_server.py toolkit/sb_core/cli.py toolkit/board/index.html tests/test_board_server.py
git commit -m "feat(board): local HTTP server with token, host check and lifecycle"
```

---
### Task 8: UI della board (`toolkit/board/index.html`)

**Files:**
- Modify: `toolkit/board/index.html` (sostituisce il segnaposto del Task 7)
- Test: `tests/test_board_ui.py`

**Interfaces:**
- Consumes: le API del Task 7 (`GET /api/snapshot`, `GET /api/version`, `POST /api/tasks`, `PATCH /api/tasks`) con header `X-SB-Token` (letto da `?t=`) e il contratto dello snapshot del Task 4 (`tasks[].path/title/status/owner/due/priority/related/created/updated/body/etag`, `enums`, `people`, `projects`, `thresholds.due_soon_days`, `sync`, `wiki.name`, `today`).
- Produces: la pagina descritta nella spec della board, §3. Non espone interfacce a codice.

- [ ] **Step 1: Scrivi il test che fallisce**

`tests/test_board_ui.py`:

```python
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from helpers import ROOT

HTML = ROOT / "toolkit" / "board" / "index.html"


class BoardUiTest(unittest.TestCase):
    def setUp(self):
        self.text = HTML.read_text(encoding="utf-8")

    def test_talks_only_to_the_local_api(self):
        for marker in ("X-SB-Token", "/api/snapshot", "/api/version", "/api/tasks", "'PATCH'", "'POST'"):
            self.assertIn(marker, self.text)
        self.assertEqual(re.findall(r"<script[^>]+src=", self.text), [])
        hosts = set(re.findall(r"https?://([^/\"')\s]+)", self.text))
        self.assertTrue(hosts <= {"fonts.googleapis.com", "fonts.gstatic.com", "www.w3.org"}, hosts)

    def test_views_quick_add_and_panel(self):
        for marker in ('data-view="status"', 'data-view="priority"', 'data-view="people"', "Aggiungi task",
                       "draggable", "Aggiungi nota", "Comando per Claude", "Mostra chiusi", "Nuovo task"):
            self.assertIn(marker, self.text)

    def test_palette(self):
        for color in ("#F2ECE3", "#F6F1EA", "#FBF8F3", "#A2461E", "#ECE4D8", "#EFE3CC", "#F1DED4", "#E5E5D4", "#E8E3DB"):
            self.assertIn(color, self.text)

    @unittest.skipUnless(shutil.which("node"), "node non disponibile")
    def test_script_parses(self):
        script = re.search(r"<script>(.*?)</script>", self.text, re.S).group(1)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as handle:
            handle.write(script)
        self.addCleanup(os.unlink, handle.name)
        proc = subprocess.run(["node", "--check", handle.name], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui il test e verifica che fallisca**

Run: `python3 -m unittest discover -s tests -p 'test_board_ui.py' -v`
Expected: FAIL su `test_talks_only_to_the_local_api`, `test_views_quick_add_and_panel` e `test_palette`: il segnaposto non contiene i marker. `test_script_parses` va in ERROR, perché `<script>` non esiste, oppure viene saltato se manca node.

- [ ] **Step 3: Scrivi la UI**

`toolkit/board/index.html`:

````html
<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Board</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --ground:#F2ECE3;--bar:#F6F1EA;--card:#FBF8F3;--card-closed:#F4EFE7;--line:#E0D5C5;--line2:#CDBFAB;
  --ink:#2A231D;--ink2:#66594D;--ink3:#8C7D6E;--accent:#A2461E;--accent-d:#8E3B17;--accent-soft:#EFD9CC;
  --sand:#ECE4D8;--sand-l:#E0D5C5;--ochre:#EFE3CC;--ochre-l:#E3D3B5;--clay:#F1DED4;--clay-l:#E5CDBF;
  --sage:#E5E5D4;--sage-l:#D5D6C0;--stone:#E8E3DB;--stone-l:#DAD2C6;
  --sans:'Instrument Sans','Helvetica Neue',system-ui,sans-serif;--mono:'IBM Plex Mono',ui-monospace,Menlo,monospace;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{background:var(--ground);color:var(--ink);font:12px/1.4 var(--sans);-webkit-font-smoothing:antialiased}
button,input,select{font:inherit;color:inherit}
button{cursor:pointer}
:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.mono{font-family:var(--mono)}
.muted{color:var(--ink2)}
.grow{flex:1}
.row{display:flex;align-items:center;gap:6px}
.app{height:100vh;display:flex;flex-direction:column}
header{display:flex;align-items:center;gap:14px;padding:0 20px;height:48px;border-bottom:1px solid var(--line);background:var(--bar);flex-shrink:0}
.brand{font-weight:600;font-size:13px;letter-spacing:-.01em;white-space:nowrap}
.seg{display:flex;gap:2px;padding:2px;border:1px solid var(--line);border-radius:7px;background:#EDE6DB}
.seg button{display:flex;align-items:center;gap:6px;height:24px;padding:0 10px;border:1px solid transparent;border-radius:5px;background:transparent;color:var(--ink2)}
.seg button[aria-pressed="true"]{background:var(--card);border-color:var(--line);color:var(--ink);font-weight:500;box-shadow:0 1px 1px rgba(74,52,30,.06)}
.seg kbd{font:10px var(--mono);color:var(--ink3)}
.search{display:flex;align-items:center;gap:6px;height:28px;padding:0 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);width:220px}
.search input{flex:1;border:0;background:transparent;outline:none;min-width:0}
.search input::placeholder,input::placeholder{color:var(--ink3)}
.filters{display:flex;gap:6px;align-items:center}
.btn{display:inline-flex;align-items:center;gap:5px;height:28px;padding:0 9px;border:1px solid var(--line);border-radius:6px;background:transparent;color:var(--ink)}
.btn:hover{border-color:var(--line2)}
.btn.sm{height:26px;padding:0 7px}
.btn.ghost{border-color:transparent;color:var(--ink2)}
.btn.ghost:hover{border-color:var(--line)}
.btn[aria-pressed="true"],.btn.on{background:#E6DCCD;border-color:var(--line2)}
.btn.primary{background:var(--accent);border-color:var(--accent-d);color:#FFF8F2;font-weight:500}
.btn.primary:hover{background:var(--accent-d)}
select.sel{appearance:none;-webkit-appearance:none;padding-right:22px;background:transparent url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%2366594D' stroke-width='2.4' stroke-linecap='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E") no-repeat right 7px center}
select.sel.on{background-color:#E6DCCD}
.sync{display:flex;align-items:center;gap:6px;color:var(--ink2);white-space:nowrap}
.led{width:6px;height:6px;border-radius:3px;background:#8A9A5B}
.led.warn{background:#C2853A}.led.off{background:#B9AA95}.led.down{background:var(--accent)}
.summary{display:flex;gap:14px;padding:10px 20px 0;color:var(--ink2);flex-shrink:0}
.summary b{font-weight:500;color:var(--ink)}
.summary b.late{color:#8A3313}
.stage{flex:1;position:relative;min-height:0;display:flex}
.board{flex:1;display:flex;gap:10px;padding:10px 20px 16px;overflow-x:auto;min-width:0}
.col{flex:1 1 0;min-width:236px;max-width:360px;display:flex;flex-direction:column;border:1px solid;border-radius:8px;min-height:0;transition:border-color .12s,box-shadow .12s}
.col.sand{background:var(--sand);border-color:var(--sand-l)}
.col.ochre{background:var(--ochre);border-color:var(--ochre-l)}
.col.clay{background:var(--clay);border-color:var(--clay-l)}
.col.sage{background:var(--sage);border-color:var(--sage-l)}
.col.stone{background:var(--stone);border-color:var(--stone-l)}
.col.over{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.col-h{display:flex;align-items:center;gap:6px;padding:7px 6px 5px 10px}
.col-h h2{margin:0;font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:#4E4339;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dot{width:7px;height:7px;border-radius:4px;flex-shrink:0}
.count{font:10.5px var(--mono);color:var(--ink2)}
.icon{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border:0;border-radius:5px;background:transparent;color:var(--ink2)}
.icon:hover{background:rgba(74,52,30,.07)}
.lane{display:flex;flex-direction:column;gap:6px;padding:0 6px 8px;overflow-y:auto;min-height:0}
.lane::-webkit-scrollbar{width:6px}.lane::-webkit-scrollbar-thumb{background:#D8CBB8;border-radius:3px}
.empty{padding:14px 8px;border:1px dashed #D3C6B3;border-radius:6px;color:var(--ink2);text-align:center}
.card{position:relative;display:flex;flex-direction:column;gap:7px;padding:9px 10px;background:var(--card);border:1px solid var(--line);border-radius:6px;box-shadow:0 1px 0 rgba(74,52,30,.05);transition:border-color .12s}
.card:hover{border-color:var(--line2)}
.card.closed{background:var(--card-closed)}
.card.sel{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-soft)}
.card.cur{outline:2px solid var(--line2);outline-offset:1px}
.card.dragging{opacity:.45}
.ttl{all:unset;cursor:pointer;padding-right:4px;font-size:12.5px;font-weight:500;line-height:1.35;text-wrap:pretty}
.card.closed .ttl{color:#7A6D60;text-decoration:line-through;text-decoration-color:#B8A894}
.ttl:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:2px}
.meta{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.chip{padding:1px 6px;border-radius:4px;font-size:10.5px;white-space:nowrap}
.chip.date{font-family:var(--mono);color:var(--ink2)}
.chip.date.late{background:#F1D9CB;color:#8A3313}
.chip.date.soon{background:#F0E2C6;color:#6F4E0F}
.chip.prio{font-weight:500}
.chip.prio.high{background:#EED3C4;color:#8A3313}
.chip.prio.medium{background:#ECE0CA;color:#6A4F17}
.chip.prio.low{background:#E6DFD5;color:#5C5248}
.chip.rel{background:#F1EBE2;border:1px solid #E5DACA;color:#5A4E43}
.chip.removable{display:inline-flex;align-items:center;gap:3px;padding-right:2px}
.chip.removable button{display:inline-flex;border:0;background:transparent;color:var(--ink2);padding:1px;border-radius:3px}
.avatar{display:flex;align-items:center;justify-content:center;width:19px;height:19px;border-radius:10px;background:#DCCBB6;color:#4E3D2F;font-size:9px;font-weight:600;letter-spacing:.02em}
.qa{position:absolute;top:6px;right:6px;display:flex;gap:2px;padding:2px;background:var(--card);border:1px solid var(--line);border-radius:6px;opacity:0;transition:opacity .12s}
.card:hover .qa,.card:focus-within .qa{opacity:1}
.qa button{display:flex;align-items:center;justify-content:center;width:22px;height:22px;border:0;border-radius:4px;background:transparent;color:var(--ink2)}
.qa button:first-child{color:var(--accent)}
.qa button:hover{background:rgba(74,52,30,.07)}
.addrow{display:flex;align-items:center;gap:6px;height:28px;padding:0 8px;border:0;border-radius:6px;background:transparent;color:var(--ink2);text-align:left}
.addrow:hover{background:rgba(74,52,30,.05);color:var(--ink)}
.qadd{display:flex;flex-direction:column;gap:6px;padding:8px;background:var(--card);border:1px solid var(--accent);border-radius:6px;box-shadow:0 0 0 2px var(--accent-soft)}
.qadd input{border:0;background:transparent;font-size:12.5px;font-weight:500;outline:none;padding:0}
.qadd .hint{color:var(--ink2);font-size:10.5px}
.panel{position:absolute;top:10px;right:14px;bottom:16px;width:340px;display:flex;flex-direction:column;background:var(--card);border:1px solid #DDD1C0;border-radius:10px;box-shadow:0 18px 40px rgba(74,52,30,.16),0 2px 6px rgba(74,52,30,.07);overflow:hidden;z-index:2}
.panel[hidden]{display:none}
.p-head{display:flex;align-items:flex-start;gap:8px;padding:14px 16px 10px}
.p-head .grow{display:flex;flex-direction:column;gap:4px;min-width:0}
.p-head .mono{font-size:10.5px}
.p-title{border:1px solid transparent;border-radius:5px;background:transparent;padding:2px 4px;margin:0 -5px;font-size:14px;font-weight:600;line-height:1.3;letter-spacing:-.005em}
.p-title:hover{border-color:var(--line)}
.p-title:focus{border-color:var(--accent);outline:none;background:#fff}
.p-fields{margin:0;padding:4px 16px 12px;display:grid;grid-template-columns:76px minmax(0,1fr);row-gap:5px;align-items:center;border-bottom:1px solid #E6DCCD}
.p-fields dt{color:var(--ink2)}
.p-fields dd{margin:0}
.p-fields input[type=date]{padding:0 6px}
.rel-list{display:flex;flex-wrap:wrap;gap:4px;padding:3px 0}
.p-body{flex:1;overflow-y:auto;padding:12px 16px;display:flex;flex-direction:column;gap:8px;min-height:0}
.p-body h3,.note-form label{margin:0;font-size:10.5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--ink2)}
.body{white-space:pre-wrap;word-break:break-word;line-height:1.5}
.note-form{display:flex;flex-direction:column;gap:6px;margin-top:4px}
.note-form input{flex:1;min-width:0;height:28px;padding:0 8px;border:1px solid var(--line);border-radius:6px;background:#fff}
.p-foot{display:flex;gap:6px;padding:10px 16px 14px;border-top:1px solid #E6DCCD}
.menu{position:absolute;z-index:5;min-width:200px;padding:4px;background:var(--card);border:1px solid #DDD1C0;border-radius:8px;box-shadow:0 12px 28px rgba(74,52,30,.16)}
.menu[hidden]{display:none}
.menu button,.menu-date{display:flex;justify-content:space-between;align-items:center;gap:12px;width:100%;height:28px;padding:0 8px;border:0;border-radius:5px;background:transparent;text-align:left}
.menu button:hover{background:rgba(74,52,30,.06)}
.menu-date input{border:1px solid var(--line);border-radius:5px;background:#fff;font-family:var(--mono);font-size:11px;padding:1px 4px}
.modal-wrap{position:fixed;inset:0;z-index:10;display:flex;align-items:flex-start;justify-content:center;padding-top:12vh}
.modal-wrap[hidden]{display:none}
.scrim{position:absolute;inset:0;background:rgba(42,35,29,.18)}
.modal{position:relative;width:440px;max-width:calc(100vw - 32px);display:flex;flex-direction:column;gap:6px;padding:18px;background:var(--card);border:1px solid #DDD1C0;border-radius:10px;box-shadow:0 24px 60px rgba(74,52,30,.22)}
.modal h2{margin:0 0 6px;font-size:14px;font-weight:600}
.modal label{color:var(--ink2);font-size:11px;margin-top:4px}
.modal input:not([type=date]){height:30px;padding:0 8px;border:1px solid var(--line);border-radius:6px;background:#fff}
.modal .grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 10px}
.modal .grid2>div{display:flex;flex-direction:column;gap:4px}
.modal .grid2 .btn{width:100%}
.multi{border:1px solid var(--line);border-radius:6px;background:#fff;padding:4px}
.row.end{justify-content:flex-end;margin-top:10px}
.toast{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:20;max-width:560px;padding:8px 12px;background:#2A231D;color:#FBF8F3;border-radius:7px;box-shadow:0 8px 24px rgba(42,35,29,.25)}
.toast.error{background:#8A3313}
.toast[hidden]{display:none}
</style>
</head>
<body>
<div class="app">
  <header>
    <span class="brand" id="brand">Board</span>
    <nav class="seg" id="views" aria-label="Vista">
      <button type="button" data-view="status" aria-pressed="true">Stato<kbd>1</kbd></button>
      <button type="button" data-view="priority" aria-pressed="false">Priorità<kbd>2</kbd></button>
      <button type="button" data-view="people" aria-pressed="false">Persone<kbd>3</kbd></button>
    </nav>
    <div class="search">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#66594D" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <label for="q" class="sr">Cerca nei task</label>
      <input id="q" type="search" placeholder="Cerca  /" autocomplete="off">
    </div>
    <div class="filters">
      <label class="sr" for="f-project">Filtra per progetto</label><select id="f-project" class="btn sel"></select>
      <label class="sr" for="f-person">Filtra per persona</label><select id="f-person" class="btn sel"></select>
      <label class="sr" for="f-priority">Filtra per priorità</label><select id="f-priority" class="btn sel"></select>
      <button type="button" class="btn" id="show-closed" aria-pressed="false">Mostra chiusi</button>
    </div>
    <span class="grow"></span>
    <div class="sync" id="sync" role="status" aria-live="polite"></div>
    <button type="button" class="btn primary" id="new-btn"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>Nuovo</button>
  </header>
  <div class="summary" id="summary"></div>
  <div class="stage">
    <main class="board" id="board" aria-label="Task"></main>
    <aside class="panel" id="panel" hidden aria-label="Dettaglio task"></aside>
  </div>
</div>
<div class="menu" id="menu" hidden></div>
<div class="modal-wrap" id="modal" hidden></div>
<div class="toast" id="toast" role="alert" hidden></div>
<script>
(function () {
  'use strict';
  var TOKEN = new URLSearchParams(location.search).get('t') || '';
  var LABEL = {
    status: { todo: 'Da fare', doing: 'In corso', blocked: 'Bloccati', done: 'Fatti', dropped: 'Abbandonati' },
    statusOne: { todo: 'Da fare', doing: 'In corso', blocked: 'Bloccato', done: 'Fatto', dropped: 'Abbandonato' },
    priority: { high: 'Alta', medium: 'Media', low: 'Bassa' }
  };
  var PRIO_RANK = { high: 0, medium: 1, low: 2 };
  var STATUS_TINT = { todo: 'sand', doing: 'ochre', blocked: 'clay', done: 'sage' };
  var PRIO_TINT = { high: 'clay', medium: 'ochre', low: 'sand' };
  var PEOPLE_TINTS = ['sand', 'ochre', 'sage', 'stone'];
  var DOT = { sand: '#B9AA95', ochre: '#C2853A', clay: '#A2461E', sage: '#8A9A5B', stone: '#C9BBA6' };
  var MONTHS = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];
  var SVG = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';
  var ICON = {
    check: SVG.replace('stroke-width="2"', 'stroke-width="2.4"') + '<path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
    cal: SVG + '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/></svg>',
    flag: SVG + '<path d="M5 21V4h11l-2 4 2 4H5"/></svg>',
    plus: SVG.replace('stroke-width="2"', 'stroke-width="2.2"') + '<path d="M12 5v14M5 12h14"/></svg>',
    x: SVG + '<path d="M6 6l12 12M18 6 6 18"/></svg>',
    xs: '<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    copy: SVG + '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/></svg>'
  };

  var store = {
    get: function (key, fallback) {
      try { var v = localStorage.getItem('sb-board:' + key); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; }
    },
    set: function (key, value) { try { localStorage.setItem('sb-board:' + key, JSON.stringify(value)); } catch (e) { /* storage non disponibile */ } }
  };

  var S = {
    snap: null, version: null, view: store.get('view', 'status'), q: '', project: '', person: '', priority: '',
    showClosed: false, selected: null, cursor: null, adding: null, stale: false, cols: {}, order: []
  };
  if (['status', 'priority', 'people'].indexOf(S.view) < 0) S.view = 'status';

  function $(id) { return document.getElementById(id); }
  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function rank(v) { return v in PRIO_RANK ? PRIO_RANK[v] : 9; }

  // date
  function toDate(iso) { return new Date(iso + 'T00:00:00Z'); }
  function isoOf(d) { return d.toISOString().slice(0, 10); }
  function days(iso) { return Math.round((toDate(iso) - toDate(S.snap.today)) / 86400000); }
  function addDays(n) { var d = toDate(S.snap.today); d.setUTCDate(d.getUTCDate() + n); return isoOf(d); }
  function nextFriday() { var n = (5 - toDate(S.snap.today).getUTCDay() + 7) % 7; return addDays(n === 0 ? 7 : n); }
  function short(iso) { var p = iso.split('-'); return (+p[2]) + ' ' + MONTHS[+p[1] - 1]; }

  // task
  function isClosed(t) { return S.snap.enums.closed.indexOf(t.status) >= 0; }
  function recentlyClosed(t) { var d = t.updated || t.created; return !!d && days(d) >= -7; }
  function initials(name) { return name.split(/\s+/).map(function (w) { return w.charAt(0); }).join('').slice(0, 2).toUpperCase(); }
  function find(path) { return S.snap ? S.snap.tasks.filter(function (t) { return t.path === path; })[0] || null : null; }
  function selectedTask() { return find(S.selected); }
  function matches(t) {
    var q = S.q.trim().toLowerCase();
    var related = t.related || [];
    if (q && [t.title, t.owner || '', related.join(' ')].join(' ').toLowerCase().indexOf(q) < 0) return false;
    if (S.project && related.indexOf(S.project) < 0) return false;
    if (S.person && t.owner !== S.person && related.indexOf(S.person) < 0) return false;
    if (S.priority === '-' && t.priority) return false;
    if (S.priority && S.priority !== '-' && t.priority !== S.priority) return false;
    return true;
  }
  function sortTasks(list) {
    return list.slice().sort(function (a, b) {
      return (a.due === null) - (b.due === null) || (a.due || '').localeCompare(b.due || '') ||
        rank(a.priority) - rank(b.priority) || a.title.localeCompare(b.title, 'it');
    });
  }
  function prioritiesByRank() { return S.snap.enums.priority.slice().sort(function (a, b) { return rank(a) - rank(b); }); }

  function columns() {
    var all = S.snap.tasks;
    var open = all.filter(function (t) { return !isClosed(t); });
    var pool = S.showClosed ? all : open;
    var e = S.snap.enums;
    var cols;
    if (S.view === 'priority') {
      cols = prioritiesByRank().map(function (v) {
        return { key: 'p:' + v, label: LABEL.priority[v] || v, tint: PRIO_TINT[v] || 'stone', field: 'priority', value: v, pool: pool,
          test: function (t) { return t.priority === v; } };
      });
      cols.push({ key: 'p:-', label: 'Senza priorità', tint: 'stone', field: 'priority', value: null, pool: pool,
        test: function (t) { return !t.priority; } });
    } else if (S.view === 'people') {
      var owners = [];
      open.forEach(function (t) { if (t.owner && owners.indexOf(t.owner) < 0) owners.push(t.owner); });
      owners.sort(function (a, b) { return a.localeCompare(b, 'it'); });
      cols = [{ key: 'o:-', label: 'Io', tint: 'clay', field: 'owner', value: null, pool: pool, test: function (t) { return !t.owner; } }]
        .concat(owners.map(function (o, i) {
          return { key: 'o:' + o, label: o, tint: PEOPLE_TINTS[i % PEOPLE_TINTS.length], field: 'owner', value: o, pool: pool,
            test: function (t) { return t.owner === o; } };
        }));
    } else {
      cols = e.status.filter(function (s) { return s !== 'dropped'; }).map(function (s) {
        var closed = e.closed.indexOf(s) >= 0;
        return { key: 's:' + s, label: (LABEL.status[s] || s) + (closed && !S.showClosed ? ' · 7 giorni' : ''),
          tint: STATUS_TINT[s] || 'stone', field: 'status', value: s, pool: all,
          test: function (t) { return t.status === s && (!closed || S.showClosed || recentlyClosed(t)); } };
      });
    }
    S.cols = {};
    S.order = [];
    cols.forEach(function (c) {
      c.tasks = sortTasks(c.pool.filter(function (t) { return matches(t) && c.test(t); }));
      S.cols[c.key] = c;
      c.tasks.forEach(function (t) { S.order.push(t.path); });
    });
    return cols;
  }

  // render
  function cardHtml(t) {
    var closed = isClosed(t);
    var soon = S.snap.thresholds.due_soon_days;
    var due = '';
    if (t.due) {
      var d = days(t.due);
      var tone = !closed && d < 0 ? ' late' : (!closed && d <= soon ? ' soon' : '');
      var label = !closed && d < 0 ? 'Scaduto · ' + short(t.due) : (!closed && d === 0 ? 'Oggi' : short(t.due));
      due = '<span class="chip date' + tone + '">' + esc(label) + '</span>';
    }
    var prio = t.priority ? '<span class="chip prio ' + esc(t.priority) + '">' + esc(LABEL.priority[t.priority] || t.priority) + '</span>' : '';
    var rel = (t.related || []).slice(0, 2).map(function (r) { return '<span class="chip rel">' + esc(r) + '</span>'; }).join('');
    var who = t.owner ? '<span class="avatar" title="' + esc(t.owner) + '">' + esc(initials(t.owner)) + '</span>' : '';
    var cls = 'card' + (closed ? ' closed' : '') + (S.selected === t.path ? ' sel' : '') + (S.cursor === t.path ? ' cur' : '');
    return '<article class="' + cls + '" draggable="true" data-path="' + esc(t.path) + '">' +
      '<button type="button" class="ttl" data-action="open">' + esc(t.title) + '</button>' +
      '<div class="meta">' + due + prio + rel + '<span class="grow"></span>' + who + '</div>' +
      '<div class="qa">' +
      '<button type="button" data-action="toggle" aria-label="' + (closed ? 'Riapri il task' : 'Segna come fatto') + '">' + ICON.check + '</button>' +
      '<button type="button" data-action="due-menu" aria-label="Cambia scadenza">' + ICON.cal + '</button>' +
      '<button type="button" data-action="prio-cycle" aria-label="Cambia priorità">' + ICON.flag + '</button>' +
      '</div></article>';
  }

  function presetLabel(c) {
    if (c.field === 'owner') return c.value ? 'Delegato a ' + c.value : 'Owner: io';
    if (c.field === 'priority') return c.value ? 'Priorità ' + (LABEL.priority[c.value] || c.value).toLowerCase() : 'Senza priorità';
    return 'Stato: ' + (LABEL.statusOne[c.value] || c.value).toLowerCase();
  }

  function columnHtml(c) {
    var adding = S.adding === c.key;
    var tail = adding
      ? '<form class="qadd" data-col="' + esc(c.key) + '">' +
        '<label class="sr" for="qadd-in">Titolo del nuovo task</label>' +
        '<input id="qadd-in" type="text" placeholder="Titolo del task" autocomplete="off" required>' +
        '<div class="row"><span class="hint">' + esc(presetLabel(c)) + '</span><span class="grow"></span>' +
        '<button type="button" class="btn ghost sm" data-action="cancel-add">Annulla</button>' +
        '<button type="submit" class="btn primary sm">Aggiungi</button></div></form>'
      : '<button type="button" class="addrow" data-action="start-add">' + ICON.plus + 'Aggiungi task</button>';
    return '<section class="col ' + c.tint + '" data-col="' + esc(c.key) + '" aria-label="' + esc(c.label) + '">' +
      '<div class="col-h"><span class="dot" style="background:' + DOT[c.tint] + '"></span>' +
      '<h2>' + esc(c.label) + '</h2><span class="count">' + c.tasks.length + '</span><span class="grow"></span>' +
      '<button type="button" class="icon" data-action="start-add" aria-label="Aggiungi un task in ' + esc(c.label) + '">' + ICON.plus + '</button></div>' +
      '<div class="lane">' + (c.tasks.length || adding ? '' : '<div class="empty">Nessun task</div>') +
      c.tasks.map(cardHtml).join('') + tail + '</div></section>';
  }

  function renderBoard() {
    if (!S.snap) return;
    $('board').innerHTML = columns().map(columnHtml).join('');
    var open = S.snap.tasks.filter(function (t) { return !isClosed(t); });
    var overdue = open.filter(function (t) { return t.due && days(t.due) < 0; }).length;
    var delegated = open.filter(function (t) { return !!t.owner; }).length;
    $('summary').innerHTML = '<span><b class="mono">' + open.length + '</b> aperti</span>' +
      '<span><b class="mono late">' + overdue + '</b> scaduti</span>' +
      '<span><b class="mono">' + delegated + '</b> delegati</span>';
    if (S.adding && $('qadd-in')) $('qadd-in').focus();
  }

  function fillSelect(el, label, options, value) {
    if (document.activeElement === el) return;
    el.innerHTML = '<option value="">' + esc(label) + ': tutti</option>' + options.map(function (o) {
      return '<option value="' + esc(o[0]) + '"' + (o[0] === value ? ' selected' : '') + '>' + esc(o[1]) + '</option>';
    }).join('');
    el.classList.toggle('on', !!value);
  }

  function renderSync(offline) {
    var el = $('sync');
    if (offline) { el.innerHTML = '<span class="led down"></span><span>Server non raggiungibile</span>'; el.title = ''; return; }
    var s = S.snap.sync, tone = '', text = 'Salvato', detail = '';
    if (!s.git) { tone = 'off'; text = 'Nessun git'; }
    else if (s.uncommitted.length) { tone = 'warn'; text = 'Commit in sospeso'; detail = s.commit_error || ''; }
    else if (s.last_error) { tone = 'warn'; text = 'Push fallito'; detail = s.last_error; }
    else if (s.pending_push) { text = 'Salvato · push in coda'; }
    el.innerHTML = '<span class="led ' + tone + '"></span><span>' + esc(text) + '</span>' +
      (s.git && s.head ? '<span class="mono">' + esc(s.head) + '</span>' : '');
    el.title = detail;
  }

  function renderHeader() {
    var snap = S.snap;
    $('brand').textContent = snap.wiki.name;
    document.title = snap.wiki.name + ' · Board';
    Array.prototype.forEach.call(document.querySelectorAll('#views button'), function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.view === S.view));
    });
    $('show-closed').setAttribute('aria-pressed', String(S.showClosed));
    fillSelect($('f-project'), 'Progetto', snap.projects.map(function (p) { return [p.title, p.title]; }), S.project);
    fillSelect($('f-person'), 'Persona', snap.people.map(function (p) { return [p.title, p.title]; }), S.person);
    fillSelect($('f-priority'), 'Priorità', prioritiesByRank().map(function (v) { return [v, LABEL.priority[v] || v]; })
      .concat([['-', 'Senza priorità']]), S.priority);
    renderSync(false);
  }

  function renderPanel(force) {
    var panel = $('panel');
    var t = selectedTask();
    if (!t) { panel.hidden = true; panel.innerHTML = ''; delete panel.dataset.path; return; }
    if (!force && panel.dataset.path === t.path && panel.contains(document.activeElement)) return;
    panel.dataset.path = t.path;
    var e = S.snap.enums;
    var people = S.snap.people.map(function (p) { return p.title; });
    if (t.owner && people.indexOf(t.owner) < 0) people.unshift(t.owner);
    var related = t.related || [];
    var candidates = S.snap.people.concat(S.snap.projects).map(function (p) { return p.title; })
      .filter(function (n) { return related.indexOf(n) < 0; });
    var statusOpts = e.status.map(function (s) {
      return '<option value="' + esc(s) + '"' + (t.status === s ? ' selected' : '') + '>' + esc(LABEL.statusOne[s] || s) + '</option>';
    }).join('');
    var ownerOpts = '<option value="">Io</option>' + people.map(function (n) {
      return '<option' + (t.owner === n ? ' selected' : '') + '>' + esc(n) + '</option>';
    }).join('');
    var prioOpts = '<option value="">Nessuna</option>' + prioritiesByRank().map(function (v) {
      return '<option value="' + esc(v) + '"' + (t.priority === v ? ' selected' : '') + '>' + esc(LABEL.priority[v] || v) + '</option>';
    }).join('');
    var chips = related.map(function (r) {
      return '<span class="chip rel removable">' + esc(r) + '<button type="button" data-action="rel-remove" data-name="' + esc(r) +
        '" aria-label="Scollega ' + esc(r) + '">' + ICON.xs + '</button></span>';
    }).join('');
    var relAdd = candidates.length
      ? '<label class="sr" for="rel-add">Collega una pagina</label><select id="rel-add" class="btn sel sm" data-field="rel-add">' +
        '<option value="">+ Collega</option>' + candidates.map(function (n) { return '<option>' + esc(n) + '</option>'; }).join('') + '</select>'
      : '';
    var body = (t.body || '').trim();
    panel.innerHTML =
      '<div class="p-head"><div class="grow"><span class="mono muted">' + esc(t.path.split('/').slice(0, -1).join('/')) + '</span>' +
      '<label class="sr" for="p-title">Titolo</label><input id="p-title" class="p-title" data-field="title" value="' + esc(t.title) + '" autocomplete="off"></div>' +
      '<button type="button" class="icon" data-action="close-panel" aria-label="Chiudi il dettaglio">' + ICON.x + '</button></div>' +
      '<dl class="p-fields">' +
      '<dt><label for="p-status">Stato</label></dt><dd><select id="p-status" class="btn sel sm" data-field="status">' + statusOpts + '</select></dd>' +
      '<dt><label for="p-owner">Owner</label></dt><dd><select id="p-owner" class="btn sel sm" data-field="owner">' + ownerOpts + '</select></dd>' +
      '<dt><label for="p-due">Scadenza</label></dt><dd class="row"><input id="p-due" type="date" class="btn sm mono" data-field="due" value="' + esc(t.due || '') + '">' +
      (t.due ? '<button type="button" class="btn ghost sm" data-action="due-clear">Nessuna</button>' : '') + '</dd>' +
      '<dt><label for="p-prio">Priorità</label></dt><dd><select id="p-prio" class="btn sel sm" data-field="priority">' + prioOpts + '</select></dd>' +
      '<dt>Collegati</dt><dd class="rel-list">' + chips + relAdd + '</dd></dl>' +
      '<div class="p-body"><h3>Note</h3>' + (body ? '<div class="body">' + esc(body) + '</div>' : '<p class="muted">Nessuna nota.</p>') +
      '<form class="note-form" id="note-form"><label for="note-in">Aggiungi nota</label>' +
      '<div class="row"><input id="note-in" type="text" placeholder="es. sollecitato in standup" autocomplete="off">' +
      '<button type="submit" class="btn sm">Aggiungi</button></div></form></div>' +
      '<div class="p-foot"><button type="button" class="btn sm" data-action="copy-cmd">' + ICON.copy + 'Comando per Claude</button></div>';
    panel.hidden = false;
  }

  function render() { renderHeader(); renderBoard(); renderPanel(false); }

  // rete
  function api(method, path, body) {
    return fetch(path, {
      method: method,
      headers: { 'X-SB-Token': TOKEN, 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body)
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) {
          var issue = data.issues && data.issues[0] ? ': ' + data.issues[0].message : '';
          var err = new Error((data.error || 'Errore ' + res.status) + issue);
          err.status = res.status;
          err.data = data;
          throw err;
        }
        return data;
      });
    });
  }

  function load() {
    return Promise.all([api('GET', '/api/snapshot'), api('GET', '/api/version')]).then(function (r) {
      S.snap = r[0];
      S.version = r[1].version;
      if (S.selected && !find(S.selected)) S.selected = null;
      render();
    }).catch(function (e) { toast(e.message, true); renderSyncIfReady(true); });
  }

  function renderSyncIfReady(offline) { if (S.snap) renderSync(offline); }

  function busy() {
    var a = document.activeElement;
    return !!(a && /INPUT|SELECT|TEXTAREA/.test(a.tagName) && a.id !== 'q' && a.closest && a.closest('#panel, .qadd, #modal'));
  }

  function poll() {
    api('GET', '/api/version').then(function (v) {
      if (v.version === S.version) { renderSyncIfReady(false); return; }
      if (busy()) { S.stale = true; return; }
      load();
    }).catch(function () { renderSyncIfReady(true); });
  }

  function replaceTask(path, task) {
    for (var i = 0; i < S.snap.tasks.length; i++) {
      if (S.snap.tasks[i].path === path) { S.snap.tasks[i] = task; return; }
    }
  }

  function applyLocal(t, set) {
    Object.keys(set).forEach(function (k) {
      var v = set[k];
      if (k === 'owner') { t.owner = v || null; t.delegated = !!v; }
      else if (k === 'related') { t.related = v || []; }
      else if (k !== 'title') { t[k] = v || null; }
    });
    t.overdue = !!(t.due && !isClosed(t) && days(t.due) < 0);
  }

  function patch(path, set, note) {
    var t = find(path);
    if (!t) return Promise.resolve();
    var before = JSON.parse(JSON.stringify(t));
    if (set) applyLocal(t, set);
    renderBoard();
    renderPanel(true);
    return api('PATCH', '/api/tasks', { path: path, etag: before.etag, set: set || {}, note: note || null }).then(function (res) {
      replaceTask(path, res.task);
      if (S.selected === path) S.selected = res.task.path;
      if (S.cursor === path) S.cursor = res.task.path;
      if (!res.committed && S.snap.sync.git) toast('Salvato, ma il commit è in sospeso');
    }).catch(function (e) {
      replaceTask(path, before);
      toast(e.status === 409 ? 'Il task è stato modificato altrove: ho ricaricato la board' : e.message, true);
    }).then(load);
  }

  function create(data) {
    return api('POST', '/api/tasks', data).then(function (res) {
      S.selected = res.task.path;
      S.adding = null;
      return load().then(function () { return true; });
    }).catch(function (e) {
      if (e.status === 409 && e.data && e.data.path) {
        toast('Esiste già un task con questo titolo: l\'ho aperto');
        S.selected = e.data.path;
        S.adding = null;
        renderBoard();
        renderPanel(true);
      } else {
        toast(e.message, true);
      }
      return false;
    });
  }

  // azioni
  function moveTo(path, col) {
    var t = find(path);
    if (!t) return;
    var current = col.field === 'owner' ? (t.owner || null) : (t[col.field] || null);
    if (current === col.value) return;
    var set = {};
    set[col.field] = col.value;
    patch(path, set);
  }

  function toggleDone(path) {
    var t = find(path);
    if (!t) return;
    var e = S.snap.enums;
    var reopen = e.status.filter(function (s) { return e.closed.indexOf(s) < 0; })[0] || 'todo';
    var close = e.status.indexOf('done') >= 0 ? 'done' : e.closed[0];
    patch(path, { status: isClosed(t) ? reopen : close });
  }

  function cyclePriority(path) {
    var t = find(path);
    if (!t) return;
    var values = [null].concat(prioritiesByRank().reverse());
    var next = values[(values.indexOf(t.priority || null) + 1) % values.length];
    patch(path, { priority: next });
  }

  function openDueMenu(anchor, path) {
    var t = find(path);
    var menu = $('menu');
    var options = [['+1 giorno', addDays(1)], ['Venerdì', nextFriday()], ['+1 settimana', addDays(7)]];
    menu.innerHTML = options.map(function (o) {
      return '<button type="button" data-action="due-set" data-value="' + o[1] + '"><span>' + o[0] + '</span><span class="mono muted">' + short(o[1]) + '</span></button>';
    }).join('') +
      '<label class="menu-date"><span>Data</span><input type="date" id="menu-date" value="' + esc(t.due || '') + '"></label>' +
      (t.due ? '<button type="button" data-action="due-set" data-value="">Nessuna scadenza</button>' : '');
    menu.dataset.path = path;
    var r = anchor.getBoundingClientRect();
    menu.style.top = (r.bottom + 4 + window.scrollY) + 'px';
    menu.style.left = Math.max(8, Math.min(r.left, window.innerWidth - 220)) + 'px';
    menu.hidden = false;
  }

  function closeMenu() { $('menu').hidden = true; }

  function setView(view) {
    S.view = view;
    S.adding = null;
    store.set('view', view);
    renderHeader();
    renderBoard();
  }

  function moveCursor(step) {
    if (!S.order.length) return;
    var i = S.order.indexOf(S.cursor);
    i = i < 0 ? 0 : Math.max(0, Math.min(S.order.length - 1, i + step));
    S.cursor = S.order[i];
    renderBoard();
    var el = document.querySelector('.card.cur');
    if (el) el.scrollIntoView({ block: 'nearest' });
  }

  function copyCommand() {
    var t = selectedTask();
    if (!t) return;
    var cmd = '/sb:tasks update "' + t.title + '" ';
    var copy = navigator.clipboard && navigator.clipboard.writeText ? navigator.clipboard.writeText(cmd) : Promise.reject();
    copy.then(function () { toast('Comando copiato: incollalo in Claude Code'); }, function () { toast(cmd); });
  }

  function openModal() {
    if (!S.snap) return;
    var s = S.snap, e = s.enums;
    var statusOpts = e.status.filter(function (st) { return e.closed.indexOf(st) < 0; }).map(function (st) {
      return '<option value="' + esc(st) + '">' + esc(LABEL.statusOne[st] || st) + '</option>';
    }).join('');
    var prioOpts = '<option value="">Nessuna</option>' + prioritiesByRank().map(function (v) {
      return '<option value="' + esc(v) + '">' + esc(LABEL.priority[v] || v) + '</option>';
    }).join('');
    var linkable = s.people.concat(s.projects).map(function (p) { return '<option>' + esc(p.title) + '</option>'; }).join('');
    $('modal').innerHTML =
      '<div class="scrim" data-action="close-modal"></div>' +
      '<form class="modal" id="new-form" aria-label="Nuovo task"><h2>Nuovo task</h2>' +
      '<label for="n-title">Titolo</label><input id="n-title" name="title" required autocomplete="off">' +
      '<div class="grid2">' +
      '<div><label for="n-status">Stato</label><select id="n-status" name="status" class="btn sel">' + statusOpts + '</select></div>' +
      '<div><label for="n-owner">Owner</label><select id="n-owner" name="owner" class="btn sel"><option value="">Io</option>' +
      s.people.map(function (p) { return '<option>' + esc(p.title) + '</option>'; }).join('') + '</select></div>' +
      '<div><label for="n-due">Scadenza</label><input id="n-due" name="due" type="date" class="btn mono"></div>' +
      '<div><label for="n-prio">Priorità</label><select id="n-prio" name="priority" class="btn sel">' + prioOpts + '</select></div>' +
      '</div>' +
      '<label for="n-related">Collegati</label><select id="n-related" name="related" multiple size="5" class="multi">' + linkable + '</select>' +
      '<label for="n-note">Nota</label><input id="n-note" name="note" autocomplete="off">' +
      '<div class="row end"><button type="button" class="btn ghost" data-action="close-modal">Annulla</button>' +
      '<button type="submit" class="btn primary">Crea task</button></div></form>';
    $('modal').hidden = false;
    $('n-title').focus();
  }

  function closeModal() { $('modal').hidden = true; $('modal').innerHTML = ''; }

  function submitNew(form) {
    var f = new FormData(form);
    var data = {
      title: String(f.get('title') || '').trim(), status: f.get('status') || null, owner: f.get('owner') || null,
      due: f.get('due') || null, priority: f.get('priority') || null, related: f.getAll('related'),
      note: String(f.get('note') || '').trim() || null
    };
    if (!data.title) return;
    create(data).then(function (ok) { if (ok) closeModal(); });
  }

  var toastTimer = null;
  function toast(message, error) {
    var el = $('toast');
    el.textContent = message;
    el.className = 'toast' + (error ? ' error' : '');
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.hidden = true; }, error ? 6000 : 3000);
  }

  // eventi
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-action], [data-view]');
    if (!$('menu').hidden && !e.target.closest('#menu') && !(el && el.dataset.action === 'due-menu')) closeMenu();
    if (!el) return;
    if (el.dataset.view) { setView(el.dataset.view); return; }
    var holder = el.closest('[data-path]');
    var path = holder ? holder.dataset.path : S.selected;
    var t;
    switch (el.dataset.action) {
      case 'open': S.selected = path; S.cursor = path; renderBoard(); renderPanel(true); break;
      case 'toggle': toggleDone(path); break;
      case 'due-menu': openDueMenu(el, path); break;
      case 'prio-cycle': cyclePriority(path); break;
      case 'due-set': closeMenu(); patch($('menu').dataset.path, { due: el.dataset.value || null }); break;
      case 'start-add': S.adding = el.closest('[data-col]').dataset.col; renderBoard(); break;
      case 'cancel-add': S.adding = null; renderBoard(); break;
      case 'close-panel': S.selected = null; renderBoard(); renderPanel(false); break;
      case 'due-clear': patch(S.selected, { due: null }); break;
      case 'rel-remove':
        t = selectedTask();
        if (t) patch(t.path, { related: (t.related || []).filter(function (r) { return r !== el.dataset.name; }) });
        break;
      case 'copy-cmd': copyCommand(); break;
      case 'close-modal': closeModal(); break;
    }
  });

  document.addEventListener('change', function (e) {
    var el = e.target;
    if (el.id === 'f-project') { S.project = el.value; el.classList.toggle('on', !!el.value); renderBoard(); return; }
    if (el.id === 'f-person') { S.person = el.value; el.classList.toggle('on', !!el.value); renderBoard(); return; }
    if (el.id === 'f-priority') { S.priority = el.value; el.classList.toggle('on', !!el.value); renderBoard(); return; }
    if (el.id === 'menu-date') { var p = $('menu').dataset.path; closeMenu(); if (el.value) patch(p, { due: el.value }); return; }
    var field = el.dataset.field;
    var t = selectedTask();
    if (!field || !t) return;
    if (field === 'title') {
      var title = el.value.trim();
      if (title && title !== t.title) patch(t.path, { title: title }); else el.value = t.title;
    } else if (field === 'rel-add') {
      if (el.value) patch(t.path, { related: (t.related || []).concat([el.value]) });
    } else {
      var set = {};
      set[field] = el.value || null;
      patch(t.path, set);
    }
  });

  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (form.classList.contains('qadd')) {
      e.preventDefault();
      var input = form.querySelector('input');
      var title = input.value.trim();
      var col = S.cols[form.dataset.col];
      if (!title || !col) return;
      var data = { title: title };
      if (col.value) data[col.field] = col.value;
      input.disabled = true;
      create(data).then(function (ok) { if (!ok) { input.disabled = false; input.focus(); } });
    } else if (form.id === 'note-form') {
      e.preventDefault();
      var note = $('note-in');
      var text = note.value.trim();
      if (!text || !S.selected) return;
      note.value = '';
      patch(S.selected, null, text);
    } else if (form.id === 'new-form') {
      e.preventDefault();
      submitNew(form);
    }
  });

  document.addEventListener('keydown', function (e) {
    var tag = e.target.tagName;
    var typing = /INPUT|SELECT|TEXTAREA/.test(tag);
    if (e.key === 'Escape') {
      if (!$('menu').hidden) { closeMenu(); return; }
      if (!$('modal').hidden) { closeModal(); return; }
      if (S.adding) { S.adding = null; renderBoard(); return; }
      if (typing) { e.target.blur(); return; }
      if (S.selected) { S.selected = null; renderBoard(); renderPanel(false); }
      return;
    }
    if (typing || e.metaKey || e.ctrlKey || e.altKey || !S.snap) return;
    if (tag === 'BUTTON' && (e.key === 'Enter' || e.key === ' ')) return;
    var k = e.key;
    if (k === '1' || k === '2' || k === '3') setView(['status', 'priority', 'people'][+k - 1]);
    else if (k === '/') { e.preventDefault(); $('q').focus(); }
    else if (k === 'n') { e.preventDefault(); openModal(); }
    else if (k === 'j' || k === 'k') moveCursor(k === 'j' ? 1 : -1);
    else if (k === 'Enter' && S.cursor) { S.selected = S.cursor; renderBoard(); renderPanel(true); }
    else if (k === 'x' && (S.cursor || S.selected)) toggleDone(S.cursor || S.selected);
  });

  var dragPath = null;
  document.addEventListener('dragstart', function (e) {
    var card = e.target.closest && e.target.closest('.card');
    if (!card) return;
    dragPath = card.dataset.path;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', dragPath);
    card.classList.add('dragging');
  });
  document.addEventListener('dragend', function () {
    dragPath = null;
    Array.prototype.forEach.call(document.querySelectorAll('.dragging, .col.over'), function (n) {
      n.classList.remove('dragging', 'over');
    });
  });
  document.addEventListener('dragover', function (e) {
    var col = e.target.closest && e.target.closest('.col');
    if (!col || !dragPath) return;
    e.preventDefault();
    Array.prototype.forEach.call(document.querySelectorAll('.col.over'), function (n) { if (n !== col) n.classList.remove('over'); });
    col.classList.add('over');
  });
  document.addEventListener('drop', function (e) {
    var col = e.target.closest && e.target.closest('.col');
    if (!col || !dragPath) return;
    e.preventDefault();
    var path = dragPath;
    dragPath = null;
    col.classList.remove('over');
    var target = S.cols[col.dataset.col];
    if (target) moveTo(path, target);
  });

  document.addEventListener('focusout', function () {
    setTimeout(function () { if (S.stale && !busy()) { S.stale = false; load(); } }, 60);
  });

  $('new-btn').addEventListener('click', openModal);
  $('show-closed').addEventListener('click', function () { S.showClosed = !S.showClosed; renderHeader(); renderBoard(); });
  $('q').addEventListener('input', function (e) { S.q = e.target.value; renderBoard(); });

  if (!TOKEN) toast('Manca il token nell\'URL: riapri la board con sb board', true);
  load();
  setInterval(poll, 5000);
})();
</script>
</body>
</html>
````

- [ ] **Step 4: Esegui tutti i test**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`. `test_script_parses` passa, oppure viene saltato se manca node.

- [ ] **Step 5: Prova manuale nel browser**

Run: `W=$(mktemp -d)/w && cp -R tests/fixtures/sample-wiki "$W" && python3 toolkit/sb.py board --wiki "$W"`

Expected: il browser si apre su una board con il nome della cartella e i 2 task della wiki di esempio. Verifica:
- le tre viste (`1`/`2`/`3`);
- il drag di una card in un'altra colonna, che cambia il file e crea un commit `sb(board): …` (`git -C "$W" log -1`), solo se `$W` è un repo git: fai prima `git -C "$W" init -q && git -C "$W" add -A && git -C "$W" commit -qm init`;
- la creazione rapida in colonna;
- il pannello: stato, scadenza, nota.

Poi Ctrl+C nel terminale.

- [ ] **Step 6: Commit**

```bash
git add toolkit/board/index.html tests/test_board_ui.py
git commit -m "feat(board): kanban UI with three views, quick add and detail panel"
```

---
### Task 9: skill `/sb:board`, `/sb:tasks` sui nuovi comandi, documentazione e scenari

**Files:**
- Create: `skills/board/SKILL.md`, `tests/scenarios/board.md`
- Modify: `skills/tasks/SKILL.md`, `references/conventions.md`, `README.md`, `tests/test_plugin_layout.py`

**Interfaces:**
- Consumes:
  - CLI `sb board` (prima riga di stdout = JSON con `url`, `pid`, `port`; oppure `already_running`);
  - `.sb/board.json`;
  - `sb tasks add` e `sb tasks update` (Task 6);
  - `/api/snapshot` per `status`.
- Produces: la skill `/sb:board [stop | status]`. L'insieme delle skill diventa `{init, status, put, sync, ask, prep, report, tasks, lint, schema, board}`.

- [ ] **Step 1: Aggiorna il test di layout e verifica che fallisca**

In `tests/test_plugin_layout.py`, dentro `test_all_commands_present`, sostituisci l'insieme atteso con:

```python
        self.assertEqual(names, {"init", "status", "put", "sync", "ask", "prep", "report", "tasks", "lint", "schema",
                                 "board"})
```

e aggiungi a `SkillsTest`:

```python
    def test_tasks_skill_uses_deterministic_commands(self):
        text = (SKILLS_DIR / "tasks" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("SB tasks add", text)
        self.assertIn("SB tasks update", text)

    def test_board_skill_controls_the_server(self):
        text = (SKILLS_DIR / "board" / "SKILL.md").read_text(encoding="utf-8")
        for marker in ("SB board", ".sb/board.json", "SIGTERM", "run_in_background"):
            self.assertIn(marker, text)
```

Run: `python3 -m unittest discover -s tests -p 'test_plugin_layout.py' -v`
Expected: FAIL su `test_all_commands_present`, `test_tasks_skill_uses_deterministic_commands` e `test_board_skill_controls_the_server`

- [ ] **Step 2: Scrivi la skill della board**

`skills/board/SKILL.md`:

````markdown
---
name: board
description: Apre, ferma o controlla la board visuale dei task della wiki Second Brain, una pagina locale nel browser per vedere, trascinare, chiudere e creare task. Usa per "apri la board", "fammi vedere i task in kanban", "chiudi la board", "la board è accesa?".
argument-hint: "[stop | status]"
---

# /sb:board: la board dei task

Argomenti: `$ARGUMENTS`

Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill. La board è un server locale (`127.0.0.1`) avviato dal toolkit. Le modifiche fatte nel browser passano dal toolkit e finiscono in commit `sb(board): …`.

## Senza argomenti: avvio

1. Controlla `.sb/board.json` nella radice della wiki. Se esiste, la board potrebbe essere già attiva: il comando del passo 2 lo verifica da solo e, se è attiva, restituisce l'URL esistente.
2. Avvia il server **in background** (Bash con `run_in_background: true`):

        SB board

   Poi leggi la prima riga dell'output: è un JSON con `url`, `port` e `pid`, oppure `already_running: true` con l'URL già attivo.
3. Il comando apre il browser da solo. In più, mostra all'utente l'URL completo (contiene il token).
4. **Prima volta in questa wiki:** proponi una volta l'alias per usare la board dal terminale senza Claude Code, da aggiungere a `~/.zshrc`:

        alias sb='python3 "<radice del plugin>/toolkit/sb.py"'

   Aggiungi anche `export SB_WIKI="<radice della wiki>"`, se l'utente vuole lanciare `sb board` da qualunque cartella. Non modificare file di configurazione senza il suo ok.

## `stop`

1. Leggi il `pid` da `.sb/board.json`. Se il file manca, la board non è attiva: dillo.
2. `kill -TERM <pid>` (SIGTERM). Il server fa il push finale e rimuove `.sb/board.json`.
3. Conferma con una riga. Se `.sb/board.json` esiste ancora dopo qualche secondo, dillo all'utente invece di forzare con `kill -9`.

## `status`

1. Leggi `.sb/board.json`. Se manca: "board non attiva".
2. Chiedi lo snapshot usando il token preso dall'URL:

        curl -s -H "X-SB-Token: <token>" "http://127.0.0.1:<port>/api/snapshot"

   Dal JSON leggi `sync`.
3. Mostra in 2–4 righe:
   - porta e URL;
   - `head`;
   - push in coda (`pending_push`) e ultimo push (`last_push`);
   - eventuali `last_error`, `commit_error` e `uncommitted`.

## Note

- La board scrive solo i campi espliciti (stato, owner, scadenza, priorità, collegati, titolo, note). Le modifiche che richiedono l'LLM si fanno da Claude Code: il pannello ha "Comando per Claude", che copia `/sb:tasks update "<titolo>" `.
- Le modifiche fatte da Claude Code o da Obsidian mentre la board è aperta compaiono nella board entro 5 secondi.
````

- [ ] **Step 3: Porta `/sb:tasks` sui comandi deterministici**

In `skills/tasks/SKILL.md` sostituisci l'intera sezione `## Azioni`, fino alla riga finale "Dopo ogni azione…" compresa, con:

````markdown
## Azioni

Le azioni usano i comandi deterministici del toolkit, gli stessi della board. Questi comandi validano, aggiornano l'indice, scrivono il log e fanno commit e push da soli: **non** eseguire il flusso di chiusura delle convenzioni dopo di loro.

- **`add <testo>`**:
  1. inferisci i campi come indicato nella prosa del tipo `task` e nella skill put, passo 5;
  2. esegui `SB tasks add --title "<titolo>" [--owner "<persona>"] [--due AAAA-MM-GG] [--priority <valore>] [--status <valore>] [--related "<titolo>"]… [--note "<contesto>"]`;
  3. se il testo ha un contesto da conservare come fonte, catturalo prima in `raw/` (`kind: dictation`) e citalo nella nota.
- **`done <task>` / `drop <task>`**:
  1. risolvi con `SB resolve "<task>" --type task`; se è ambiguo, mostra i candidati e chiedi;
  2. esegui `SB tasks update "<path>" --set status=done` (oppure `status=dropped`), aggiungendo `--note "chiuso"` o `--note "abbandonato: <motivo>"`.
- **`update <task> <modifica>`**:
  1. risolvi come sopra;
  2. traduci la richiesta in `--set campo=valore` (campi: `title`, `status`, `owner`, `due`, `priority`, `related=A,B`) e `--unset campo`, più `--note "<cosa è cambiato>"`.

  Un cambio di `title` rinomina il file e riscrive i link in automatico.

Se il comando esce con codice 2, mostra il campo `error` del JSON. Per un duplicato, il campo `path` indica il task già esistente. Se la risposta ha `committed: false`, segnala che il commit è in sospeso. Conferma in una riga cosa è cambiato.
````

- [ ] **Step 4: Aggiorna convenzioni, README e scenari**

In `references/conventions.md`, nella tabella dei comandi, dopo la riga di `SB tasks list`, aggiungi:

```markdown
| `SB tasks add --title T [--owner …] [--due …] [--priority …] [--status …] [--related …]… [--note …]` | Crea un task con campi espliciti; valida, logga e fa commit da solo |
| `SB tasks update <path> [--set campo=valore]… [--unset campo]… [--note …]` | Modifica un task; valida, logga e fa commit da solo |
| `SB board [--port N] [--no-open]` | Avvia la board dei task nel browser |
```

e sotto la tabella aggiungi la riga:

```markdown
Il path della wiki si risolve così: `--wiki`, poi la variabile `SB_WIKI`, poi la cartella corrente o una sua cartella madre.
```

In `README.md`, nella tabella dei comandi, dopo la riga di `/sb:tasks`, aggiungi:

```markdown
| `/sb:board [stop \| status]` | Board kanban locale nel browser: viste Stato, Priorità, Persone |
```

e prima di `## Sviluppo` aggiungi:

```markdown
## Board dei task

`/sb:board` (oppure `python3 <plugin>/toolkit/sb.py board` da terminale) apre una board locale su `http://127.0.0.1:8765`. Puoi trascinare le card tra le colonne, chiuderle, creare task in ogni colonna e aprire un pannello di dettaglio. Ogni modifica è validata e committata (`sb(board): …`); il push parte al massimo una volta al minuto e all'arresto. Con `export SB_WIKI=<cartella della wiki>` il comando funziona da qualunque cartella.
```

`tests/scenarios/board.md`:

````markdown
# Scenari della board

Prepara una copia della wiki di esempio e avvia la board:

```bash
eval "$(tests/scenarios/setup.sh | grep -E '^(WIKI|REPO)=')"
python3 "$REPO/toolkit/sb.py" board --wiki "$WIKI"
```

`SB` sta per `python3 "$REPO/toolkit/sb.py" --wiki "$WIKI"`. In un secondo terminale, nella cartella `$WIKI`, esegui le verifiche.

## B1 · Triage nelle tre viste
1. Vista **Stato**: trascina "Preparare il budget Q4" in **In corso**.
2. Vista **Priorità** (`2`): trascina lo stesso task in **Media**.
3. Vista **Persone** (`3`): trascina "Ricevere da Luca la stima della migrazione DB" in **Io**.

Verifiche:
- `git log --format=%s -3` mostra tre commit `sb(board): …`;
- `SB tasks list --view all` riporta `status: doing` e `priority: medium` sul budget, e nessun owner sulla stima;
- `SB validate` esce con 0.

## B2 · Creazione rapida in colonna
Vista Persone, colonna **Luca Bianchi**: "Aggiungi task", scrivi "Rivedere il piano on-call", poi Invio.

Verifiche:
- esiste `operations/tasks/Rivedere il piano on-call.md` con `owner: "[[Luca Bianchi]]"`;
- il pannello di dettaglio si apre sul nuovo task.

## B3 · Pannello di dettaglio
Sul task del budget:
- imposta la scadenza a una data;
- collega "Migrazione DB";
- aggiungi la nota "sentito il controllo di gestione".

Verifiche:
- il file contiene `- <oggi>: sentito il controllo di gestione` e `related` include `[[Migrazione DB]]`;
- i commenti e i campi non toccati sono rimasti identici (`git diff HEAD~3 -- "operations/tasks/Preparare il budget Q4.md"`).

## B4 · Conflitto con una modifica esterna
Con la board aperta, modifica a mano `operations/tasks/Preparare il budget Q4.md` (per esempio la priorità). Poi, **prima che passino 5 secondi**, chiudi il task dalla board.

Verifiche:
- la board mostra "Il task è stato modificato altrove" e si ricarica;
- la modifica esterna non è stata sovrascritta.

## B5 · Arresto con push
Aggiungi un remote nudo (`git init --bare /tmp/r.git && git remote add origin /tmp/r.git`), fai una modifica dalla board e premi Ctrl+C entro 60 secondi.

Verifiche:
- `git --git-dir /tmp/r.git log -1 --format=%s` mostra l'ultimo commit `sb(board): …`;
- `.sb/board.json` non esiste più.

## B6 · Da Claude Code
`/sb:board`, poi `/sb:board status`, poi `/sb:board stop`.

Verifiche:
- l'URL viene mostrato e il browser si apre;
- `status` riporta porta e stato del push;
- dopo `stop`, `.sb/board.json` non esiste più.
````

- [ ] **Step 5: Esegui tutti i test e valida il plugin**

Run: `python3 -m unittest discover -s tests -v && claude plugin validate skills --strict && claude plugin validate .claude-plugin/plugin.json --strict`
Expected: tutti `ok`; entrambe le validazioni passano.

- [ ] **Step 6: Commit**

```bash
git add skills/board skills/tasks references/conventions.md README.md tests/scenarios/board.md tests/test_plugin_layout.py
git commit -m "feat(skills): /sb:board and deterministic /sb:tasks actions"
```
