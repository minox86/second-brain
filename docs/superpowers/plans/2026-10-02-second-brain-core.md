# Second Brain Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Costruire il plugin Claude Code `sb`: un toolkit Python deterministico, il preset Head of Engineering e le dieci skill (`init`, `status`, `put`, `sync`, `ask`, `prep`, `report`, `tasks`, `lint`, `schema`) che trasformano Claude Code nel pannello di controllo di una wiki LLM.

**Architecture:** Il repo è il plugin; ogni wiki è un repo separato creato da `/sb:init`. Il toolkit `toolkit/sb.py` (package `toolkit/sb_core/`) fa il lavoro meccanico: parse del frontmatter, validazione contro lo schema, indice, risoluzione dei nomi, query sui task, sorgenti stantie, lint strutturale, migrazioni, scaffold. Le skill (Markdown) fanno il lavoro semantico e invocano il toolkit, che risponde sempre in JSON.

**Tech Stack:** Python ≥ 3.9 solo standard library (`unittest` per i test), Markdown + frontmatter YAML ristretto, plugin Claude Code (`.claude-plugin/plugin.json`, `skills/*/SKILL.md`), git.

**Spec:** `docs/superpowers/specs/2026-10-02-second-brain-core-design.md`

## Global Constraints

- Python ≥ 3.9 (`/usr/bin/python3` di macOS è 3.9.6): niente `match`, niente `X | Y` nei type hint, niente dipendenze esterne.
- Ogni comando del toolkit stampa JSON su stdout (`ensure_ascii=False`, `indent=2`); exit `0` ok, `1` problemi trovati, `2` errore d'uso o d'ambiente (JSON `{"error": "..."}` + messaggio su stderr).
- Nome del plugin: `sb`; comandi `/sb:<skill>`; versione iniziale `0.1.0` (stessa in `plugin.json` e `sb_core.__version__`).
- Formato wiki: `schema/VERSION` = `1` (`FORMAT_VERSION = 1`).
- Nome file di una pagina = `title` + `.md`; i titoli non contengono `\ / : * ? " < > | # ^ [ ]` e sono unici in tutta la wiki (confronto case-insensitive).
- Wikilink sempre verso il titolo canonico: `[[Titolo]]`, alias con `[[Titolo|alias]]`.
- Layer: `knowledge`, `operations`; tipi predefiniti `briefing` (`outputs/briefings`) e `report` (`outputs/reports`); tipi di sistema obbligatori `task` e `source-note`.
- Soglie di default: `stale_operations_days: 30`, `one_on_one_gap_days: 21`, `due_soon_days: 7`; soglia sorgenti di default 30 giorni; `url:` e `mail:` non diventano mai stantie.
- Stati chiusi di default per i campi `status`: `[done, dropped]`, sovrascrivibili con `closed: [...]` nello spec del campo.
- Testi rivolti all'utente (messaggi del toolkit, skill, template) in italiano.
- Test: `python3 -m unittest discover -s tests -v` dalla radice del repo.

## Review Focus

1. **File con BOM o fine riga CRLF** (copiati da Windows, Teams o editor vari): il frontmatter va riconosciuto comunque, non segnalato come mancante. Test in Task 2.
2. **Wikilink non quotati nel frontmatter**, come li scrive Obsidian (`owner: [[Luca]]`, liste a blocco `- [[A]]`): vanno letti come stringhe, non come liste annidate. Test in Task 2.
3. **Nomi con accenti e differenze di maiuscole** su filesystem case-insensitive (macOS): `Nicolo` deve trovare `Nicolò`, mentre `Luca.md` e `luca.md` in cartelle diverse sono un titolo duplicato. Test in Task 4 e Task 6.
4. **Date non ISO scritte dall'LLM o dall'utente** (`due: venerdì`): `tasks list` non deve rompersi (`due: null`, `overdue: false`) e `validate` deve segnalarle. Test in Task 4 e Task 7.
5. **Toolkit lanciato da una sottocartella della wiki** (Claude Code aperto in `knowledge/people`) **o in una cartella appena clonata con solo `.git`**: va trovata la radice risalendo le cartelle, e `scaffold` deve accettare una cartella che contiene solo `.git`. Test in Task 3 e Task 11.

---

## File Structure

```
second-brain/
├── .claude-plugin/plugin.json          # manifest plugin "sb"                         (Task 1)
├── .claude-plugin/marketplace.json     # marketplace "second-brain" → plugin sb       (Task 1)
├── .gitignore                                                                          (Task 1)
├── README.md                           # installazione e uso                           (Task 1, 17)
├── toolkit/sb.py                       # entry point CLI                               (Task 1)
├── toolkit/sb_core/__init__.py         # __version__, FORMAT_VERSION                   (Task 1)
├── toolkit/sb_core/errors.py           # gerarchia eccezioni SbError                   (Task 1)
├── toolkit/sb_core/cli.py              # argparse, dispatch, JSON, exit code           (Task 1, esteso in 3–11)
├── toolkit/sb_core/frontmatter.py      # parse/dump YAML ristretto                     (Task 2)
├── toolkit/sb_core/names.py            # norm/fold, regole sui titoli                  (Task 3)
├── toolkit/sb_core/links.py            # wikilink: parse, estrazione, grafo            (Task 3, 5)
├── toolkit/sb_core/wiki.py             # Wiki, TypeDef, Page, caricamento schema       (Task 3)
├── toolkit/sb_core/validate.py         # validate                                      (Task 4)
├── toolkit/sb_core/index.py            # index.md + .sb/backlinks.json                 (Task 5)
├── toolkit/sb_core/resolve.py          # resolve                                       (Task 6)
├── toolkit/sb_core/tasks.py            # tasks list                                    (Task 7)
├── toolkit/sb_core/sources.py          # sources stale                                 (Task 8)
├── toolkit/sb_core/log.py              # log                                           (Task 8)
├── toolkit/sb_core/lint.py             # lint strutturale                              (Task 9)
├── toolkit/sb_core/status.py           # dati del cruscotto                            (Task 9)
├── toolkit/sb_core/migrate.py          # migrazioni                                    (Task 10)
├── toolkit/sb_core/scaffold.py         # creazione wiki                                (Task 11)
├── templates/wiki/CLAUDE.md            # CLAUDE.md delle wiki generate                 (Task 11)
├── presets/head-of-engineering/        # cartella schema completa                      (Task 12)
├── references/conventions.md           # regole comuni lette da tutte le skill         (Task 13)
├── skills/{init,status}/SKILL.md                                                       (Task 13)
├── skills/{put,sync}/SKILL.md                                                          (Task 14)
├── skills/{ask,prep,report,tasks}/SKILL.md                                             (Task 15)
├── skills/{lint,schema}/SKILL.md                                                       (Task 16)
└── tests/
    ├── helpers.py                      # WikiCase, md(), BASE_SCHEMA, run_cli          (Task 1, 3)
    ├── test_*.py                       # un file per modulo
    ├── fixtures/sample-wiki/           # wiki di esempio per gli scenari               (Task 17)
    └── scenarios/                      # scenari di accettazione delle skill           (Task 17)
```

---

### Task 1: Scheletro del plugin e CLI minima

**Files:**
- Create: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.gitignore`, `README.md`
- Create: `toolkit/sb.py`, `toolkit/sb_core/__init__.py`, `toolkit/sb_core/errors.py`, `toolkit/sb_core/cli.py`
- Create: `tests/helpers.py`, `tests/test_plugin_layout.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `sb_core.__version__ = "0.1.0"`, `sb_core.FORMAT_VERSION = 1`; `errors.SbError`, `errors.UsageError`, `errors.WikiError`, `errors.PlanError`, `errors.FrontmatterError` (tutte sottoclassi di `SbError`; `FrontmatterError` anche di `ValueError`); `cli.main(argv=None) -> int`; `cli.COMMANDS` (lista di funzioni `register(sub, common)`); `cli.UsageError`; helper di test `helpers.ROOT`, `helpers.run_cli(*argv) -> (code, data, stderr)`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/helpers.py`:

```python
"""Helper condivisi dai test del toolkit."""
import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "toolkit"))

from sb_core.cli import main  # noqa: E402


def run_cli(*argv):
    """Esegue la CLI in-process. Ritorna (exit_code, json_stdout | None, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main([str(a) for a in argv])
        except SystemExit as exc:  # argparse su errori d'uso o --help
            code = exc.code
    text = out.getvalue().strip()
    data = json.loads(text) if text.startswith("{") else None
    return code, data, err.getvalue()
```

`tests/test_plugin_layout.py`:

```python
import json
import unittest

from helpers import ROOT

import sb_core


class ManifestTest(unittest.TestCase):
    def test_plugin_manifest(self):
        manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "sb")
        self.assertEqual(manifest["version"], sb_core.__version__)
        self.assertTrue(manifest["description"])

    def test_marketplace_points_to_repo_root(self):
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(market["name"], "second-brain")
        plugins = {p["name"]: p for p in market["plugins"]}
        self.assertEqual(plugins["sb"]["source"], "./")


if __name__ == "__main__":
    unittest.main()
```

`tests/test_cli.py`:

```python
import subprocess
import sys
import unittest

from helpers import ROOT, run_cli

import sb_core


class CliTest(unittest.TestCase):
    def test_version(self):
        code, data, _ = run_cli("version")
        self.assertEqual(code, 0)
        self.assertEqual(data["toolkit"], sb_core.__version__)
        self.assertEqual(data["format"], 1)

    def test_unknown_command_is_usage_error(self):
        code, _, _ = run_cli("boh")
        self.assertEqual(code, 2)

    def test_entry_point_runs_as_script(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "toolkit" / "sb.py"), "version"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('"toolkit"', proc.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -v`
Expected: ERROR `ModuleNotFoundError: No module named 'sb_core'`

- [ ] **Step 3: Implementa lo scheletro**

`.claude-plugin/plugin.json`:

```json
{
  "name": "sb",
  "version": "0.1.0",
  "description": "Second Brain: Claude Code come pannello di controllo di una wiki LLM per il management (Head of Engineering).",
  "author": { "name": "Mattia Minotti" },
  "repository": "https://github.com/minox86/second-brain",
  "keywords": ["second-brain", "llm-wiki", "obsidian", "management"]
}
```

`.claude-plugin/marketplace.json`:

```json
{
  "name": "second-brain",
  "owner": { "name": "Mattia Minotti" },
  "plugins": [
    {
      "name": "sb",
      "source": "./",
      "description": "Second Brain: wiki LLM per il management, gestita da Claude Code."
    }
  ]
}
```

`.gitignore`:

```
__pycache__/
*.pyc
.DS_Store
```

`README.md`:

```markdown
# Second Brain (`sb`)

Plugin Claude Code che trasforma Claude Code nel pannello di controllo di una wiki LLM
per il lavoro di management. Design: `docs/superpowers/specs/2026-10-02-second-brain-core-design.md`.

## Requisiti

- Claude Code
- Python 3.9 o superiore (`python3`), git

## Sviluppo

    python3 -m unittest discover -s tests -v
```

`toolkit/sb_core/__init__.py`:

```python
"""Toolkit deterministico di Second Brain."""

__version__ = "0.1.0"
FORMAT_VERSION = 1
```

`toolkit/sb_core/errors.py`:

```python
"""Eccezioni del toolkit. La CLI trasforma ogni SbError in exit code 2."""


class SbError(Exception):
    """Base di tutti gli errori d'uso o d'ambiente del toolkit."""


class UsageError(SbError):
    """Argomenti non validi."""


class WikiError(SbError):
    """La wiki manca, è incompatibile o ha uno schema non valido."""


class PlanError(SbError):
    """Piano di migrazione non valido o non applicabile."""


class FrontmatterError(SbError, ValueError):
    """Frontmatter non conforme al sottoinsieme YAML supportato."""
```

`toolkit/sb_core/cli.py`:

```python
"""Interfaccia a riga di comando: argomenti, dispatch, output JSON, exit code."""
import argparse
import datetime
import json
import sys

from . import FORMAT_VERSION, __version__
from .errors import SbError, UsageError


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result, code = args.handler(args)
    except SbError as exc:
        print(f"sb: {exc}", file=sys.stderr)
        _emit({"error": str(exc)})
        return 2
    _emit(result)
    return code


def _emit(data):
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _today(args):
    value = getattr(args, "today", None)
    if not value:
        return datetime.date.today()
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise UsageError("--today deve essere nel formato AAAA-MM-GG")


def build_parser():
    parser = argparse.ArgumentParser(prog="sb", description="Toolkit deterministico di Second Brain")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--wiki", default=".", help="cartella della wiki o una sua sottocartella (default: .)")
    common.add_argument("--today", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", metavar="<comando>")
    sub.required = True
    for register in COMMANDS:
        register(sub, common)
    return parser


def _add_version(sub, common):
    p = sub.add_parser("version", parents=[common], help="versione del toolkit")
    p.set_defaults(handler=cmd_version)


def cmd_version(args):
    return {"toolkit": __version__, "format": FORMAT_VERSION}, 0


COMMANDS = [_add_version]
```

`toolkit/sb.py`:

```python
#!/usr/bin/env python3
"""Punto d'ingresso del toolkit Second Brain: python3 sb.py <comando> [opzioni]."""
import os
import sys

if sys.version_info < (3, 9):
    sys.stderr.write("sb: serve Python 3.9 o superiore\n")
    sys.exit(2)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sb_core.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
```

Poi: `chmod +x toolkit/sb.py`

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: 5 test, tutti `ok`

- [ ] **Step 5: Valida il manifest con Claude Code**

Run: `claude plugin validate .`
Expected: nessun errore. Sono accettabili avvisi sull'assenza di skill, che arrivano nei task successivi. Se il comando segnala campi non riconosciuti in `plugin.json` o `marketplace.json`, rimuovi quei campi e riesegui gli unit test.

- [ ] **Step 6: Commit**

```bash
git add .claude-plugin .gitignore README.md toolkit tests
git commit -m "feat: plugin skeleton and minimal sb CLI"
```

---

### Task 2: Parser e serializzatore del frontmatter

**Files:**
- Create: `toolkit/sb_core/frontmatter.py`
- Test: `tests/test_frontmatter.py`

**Interfaces:**
- Consumes: `errors.FrontmatterError`
- Produces: `split(text) -> (str | None, str)`; `parse(text) -> (dict | None, str)` (meta `None` se il frontmatter manca); `parse_value(text) -> object`; `dump(meta: dict) -> str` (righe YAML, ogni riga terminata da `\n`, senza delimitatori); `render(meta: dict, body: str) -> str` (`"---\n" + dump + "---\n" + body`). Le date restano stringhe `"AAAA-MM-GG"`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_frontmatter.py`:

```python
import unittest

import helpers  # noqa: F401  (configura sys.path)
from sb_core.errors import FrontmatterError
from sb_core.frontmatter import dump, parse, render


class ParseTest(unittest.TestCase):
    def test_scalars(self):
        meta, body = parse(
            "---\ntitle: Luca Bianchi\nversion: 42\nratio: 0.5\nactive: true\n"
            "none: null\ncreated: 2026-10-02\n---\nCorpo\n"
        )
        self.assertEqual(meta, {
            "title": "Luca Bianchi", "version": 42, "ratio": 0.5, "active": True,
            "none": None, "created": "2026-10-02",
        })
        self.assertEqual(body, "Corpo\n")

    def test_no_frontmatter(self):
        self.assertEqual(parse("# Titolo\n"), (None, "# Titolo\n"))

    def test_empty_frontmatter(self):
        self.assertEqual(parse("---\n---\nx"), ({}, "x"))

    def test_unclosed(self):
        with self.assertRaises(FrontmatterError):
            parse("---\ntitle: x\n")

    def test_flow_lists_with_quoted_wikilinks(self):
        meta, _ = parse(
            '---\nrelated: ["[[Migrazione DB]]", "[[2026-10-02 1on1 Luca]]"]\n'
            'sources: [raw/2026/10/x, "jira:PLAT-123", jira:PLAT-9]\n---\n'
        )
        self.assertEqual(meta["related"], ["[[Migrazione DB]]", "[[2026-10-02 1on1 Luca]]"])
        self.assertEqual(meta["sources"], ["raw/2026/10/x", "jira:PLAT-123", "jira:PLAT-9"])

    def test_unquoted_wikilinks_like_obsidian(self):
        meta, _ = parse('---\nowner: [[Luca Bianchi]]\nrelated:\n  - [[A]]\n  - "[[B|b]]"\n---\n')
        self.assertEqual(meta["owner"], "[[Luca Bianchi]]")
        self.assertEqual(meta["related"], ["[[A]]", "[[B|b]]"])

    def test_block_mapping_with_flow_maps(self):
        meta, _ = parse(
            "---\nname: person\nfields:\n  role: {kind: string}\n"
            "  status: {kind: enum, values: [active, left], default: active}\n---\n"
        )
        self.assertEqual(meta["fields"], {
            "role": {"kind": "string"},
            "status": {"kind": "enum", "values": ["active", "left"], "default": "active"},
        })

    def test_nested_flow_map(self):
        meta, _ = parse("---\nsources:\n  conf-eng: {system: confluence, scope: ENG, covers: [process]}\n---\n")
        self.assertEqual(meta["sources"]["conf-eng"], {"system": "confluence", "scope": "ENG", "covers": ["process"]})

    def test_empty_collections(self):
        meta, _ = parse("---\na: []\nb: {}\nc:\n---\n")
        self.assertEqual(meta, {"a": [], "b": {}, "c": None})

    def test_comments(self):
        meta, _ = parse('---\n# commento\nstatus: todo   # stato\ntitle: "Issue #12"\nnote: C#\n---\n')
        self.assertEqual(meta, {"status": "todo", "title": "Issue #12", "note": "C#"})

    def test_apostrophe_in_unquoted_text(self):
        meta, _ = parse("---\ntitle: L'idea di Luca # nota\n---\n")
        self.assertEqual(meta["title"], "L'idea di Luca")

    def test_single_and_double_quotes(self):
        meta, _ = parse("---\na: 'It''s ok'\nb: \"riga\\nnuova \\\"x\\\"\"\n---\n")
        self.assertEqual(meta, {"a": "It's ok", "b": 'riga\nnuova "x"'})

    def test_colon_in_unquoted_value(self):
        meta, _ = parse("---\nnote: Ore 10: standup\n---\n")
        self.assertEqual(meta["note"], "Ore 10: standup")

    def test_crlf_and_bom(self):
        self.assertEqual(parse("\ufeff---\r\ntitle: X\r\n---\r\nCorpo\r\n"), ({"title": "X"}, "Corpo\n"))

    def test_errors(self):
        for bad in [
            "---\n  indent: x\n---\n",
            "---\nlist: [a, b\n---\n",
            "---\nnokey\n---\n",
            "---\nm:\n  - a\n  b: c\n---\n",
            "---\nm:\n  b:\n---\n",
            '---\na: "aperta\n---\n',
        ]:
            with self.subTest(bad=bad):
                with self.assertRaises(FrontmatterError):
                    parse(bad)


class DumpTest(unittest.TestCase):
    def test_round_trip(self):
        meta = {
            "type": "task", "title": "Chiedere a Luca, subito", "owner": "[[Luca Bianchi]]",
            "due": "2026-10-09", "version": 42, "done": False,
            "related": ["[[Migrazione DB]]", "jira:PLAT-1"],
            "fields": {"status": {"kind": "enum", "values": ["a", "b"]}},
            "empty": None, "note": "Issue #12", "num_string": "42", "colon": "Ore 10: standup",
            "quote": 'detto "ciao"',
        }
        self.assertEqual(parse(render(meta, "Corpo\n")), (meta, "Corpo\n"))

    def test_plain_strings_stay_unquoted(self):
        self.assertEqual(
            dump({"title": "Luca Bianchi", "created": "2026-10-02", "sources": ["raw/2026/10/x"]}),
            "title: Luca Bianchi\ncreated: 2026-10-02\nsources: [raw/2026/10/x]\n",
        )

    def test_wikilinks_are_quoted(self):
        self.assertEqual(dump({"owner": "[[Luca]]"}), 'owner: "[[Luca]]"\n')


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_frontmatter.py' -v`
Expected: ERROR `ModuleNotFoundError: No module named 'sb_core.frontmatter'`

- [ ] **Step 3: Implementa il modulo**

`toolkit/sb_core/frontmatter.py`:

```python
"""Parser e serializzatore del sottoinsieme YAML usato nel frontmatter.

Grammatica supportata:
- righe `chiave: valore` al primo livello;
- `chiave:` seguita da un blocco indentato: una lista (`- valore`) oppure
  una mappa di un solo livello (`sotto: valore`);
- valori: stringhe tra virgolette o nude, interi, decimali, true/false,
  null/~, liste `[a, b]` e mappe `{k: v}` annidabili;
- commenti `#` a inizio riga o preceduti da spazio, fuori dalle virgolette.
Un valore nudo che inizia con `[[` è una stringa (wikilink).
Le date restano stringhe.
"""
import re

from .errors import FrontmatterError

_INT = re.compile(r"-?\d+$")
_FLOAT = re.compile(r"-?\d+\.\d+$")
_RESERVED = {"", "null", "~", "true", "false"}
_QUOTE_OPENERS = " \t[{,:"


def split(text):
    """Separa frontmatter e corpo. Ritorna (testo_frontmatter | None, corpo)."""
    text = text.replace("\r\n", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]
    if not text.startswith("---\n"):
        return None, text
    lines = text.split("\n")
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    raise FrontmatterError("frontmatter non chiuso: manca la riga '---'")


def parse(text):
    """Ritorna (meta | None, corpo). meta è None se il frontmatter manca."""
    fm, body = split(text)
    if fm is None:
        return None, body
    return _parse_mapping(fm), body


def _parse_mapping(src):
    result = {}
    lines = src.split("\n")
    i = 0
    while i < len(lines):
        line = _strip_comment(lines[i])
        if not line.strip():
            i += 1
            continue
        if line[0] in " \t":
            raise FrontmatterError(f"riga {i + 1}: indentazione inattesa")
        key, rest = _split_key(line, i + 1)
        i += 1
        if rest:
            result[key] = parse_value(rest)
            continue
        block = []
        while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
            stripped = _strip_comment(lines[i]).strip()
            if stripped:
                block.append((i + 1, stripped))
            i += 1
        result[key] = _parse_block(block)
    return result


def _split_key(line, lineno):
    key, sep, rest = line.partition(":")
    key = key.strip()
    if not sep or not key:
        raise FrontmatterError(f"riga {lineno}: attesa 'chiave: valore'")
    return key, rest.strip()


def _parse_block(block):
    if not block:
        return None
    if all(text == "-" or text.startswith("- ") for _, text in block):
        items = []
        for lineno, text in block:
            if text == "-":
                raise FrontmatterError(f"riga {lineno}: elemento di lista vuoto")
            items.append(parse_value(text[2:]))
        return items
    if any(text == "-" or text.startswith("- ") for _, text in block):
        raise FrontmatterError(f"riga {block[0][0]}: lista e mappa mescolate nello stesso blocco")
    mapping = {}
    for lineno, text in block:
        key, rest = _split_key(text, lineno)
        if not rest:
            raise FrontmatterError(f"riga {lineno}: annidamento oltre un livello non supportato")
        mapping[key] = parse_value(rest)
    return mapping


def _strip_comment(line):
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if quote == '"' and ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'" and (i == 0 or line[i - 1] in _QUOTE_OPENERS):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
        i += 1
    return line


def parse_value(text):
    """Interpreta un valore (scalare, lista o mappa) scritto su una riga."""
    text = text.strip()
    value, pos = _parse(text, 0, "")
    if text[pos:].strip():
        raise FrontmatterError(f"contenuto inatteso dopo il valore: {text[pos:]!r}")
    return value


def _skip_ws(s, pos):
    while pos < len(s) and s[pos] in " \t":
        pos += 1
    return pos


def _parse(s, pos, stops):
    pos = _skip_ws(s, pos)
    if pos >= len(s):
        if stops:
            raise FrontmatterError("valore mancante")
        return None, pos
    ch = s[pos]
    if ch == "[" and not s.startswith("[[", pos):
        return _parse_list(s, pos + 1)
    if ch == "{":
        return _parse_map(s, pos + 1)
    if ch in "\"'":
        return _parse_quoted(s, pos)
    end = _scalar_end(s, pos, stops)
    return _scalar(s[pos:end].strip()), end


def _parse_list(s, pos):
    items = []
    pos = _skip_ws(s, pos)
    if pos < len(s) and s[pos] == "]":
        return items, pos + 1
    while True:
        value, pos = _parse(s, pos, ",]")
        items.append(value)
        pos = _skip_ws(s, pos)
        if pos >= len(s):
            raise FrontmatterError("lista non chiusa: manca ']'")
        if s[pos] == ",":
            pos += 1
            continue
        if s[pos] == "]":
            return items, pos + 1
        raise FrontmatterError(f"carattere inatteso nella lista: {s[pos]!r}")


def _parse_map(s, pos):
    mapping = {}
    pos = _skip_ws(s, pos)
    if pos < len(s) and s[pos] == "}":
        return mapping, pos + 1
    while True:
        colon = s.find(":", pos)
        if colon == -1:
            raise FrontmatterError("mappa non valida: manca ':'")
        key = s[pos:colon].strip()
        if not key:
            raise FrontmatterError("mappa non valida: chiave vuota")
        value, pos = _parse(s, colon + 1, ",}")
        mapping[key] = value
        pos = _skip_ws(s, pos)
        if pos >= len(s):
            raise FrontmatterError("mappa non chiusa: manca '}'")
        if s[pos] == ",":
            pos = _skip_ws(s, pos + 1)
            continue
        if s[pos] == "}":
            return mapping, pos + 1
        raise FrontmatterError(f"carattere inatteso nella mappa: {s[pos]!r}")


def _parse_quoted(s, pos):
    quote = s[pos]
    out = []
    i = pos + 1
    while i < len(s):
        ch = s[i]
        if quote == '"' and ch == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            out.append({"n": "\n", "t": "\t"}.get(nxt, nxt))
            i += 2
            continue
        if ch == quote:
            if quote == "'" and s.startswith("''", i):
                out.append("'")
                i += 2
                continue
            return "".join(out), i + 1
        out.append(ch)
        i += 1
    raise FrontmatterError("stringa tra virgolette non chiusa")


def _scalar_end(s, pos, stops):
    i = pos
    while i < len(s):
        if s.startswith("[[", i):
            close = s.find("]]", i)
            if close == -1:
                raise FrontmatterError("wikilink non chiuso: manca ']]'")
            i = close + 2
            continue
        if s[i] in stops:
            break
        i += 1
    return i


def _scalar(token):
    if token in ("", "null", "~"):
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    if _INT.match(token):
        return int(token)
    if _FLOAT.match(token):
        return float(token)
    return token


def dump(meta):
    """Serializza una mappa nel sottoinsieme YAML. Le mappe di primo livello diventano blocchi."""
    lines = []
    for key, value in meta.items():
        if isinstance(value, dict) and value:
            lines.append(f"{key}:")
            for sub, subvalue in value.items():
                lines.append(f"  {sub}: {_flow(subvalue)}")
        else:
            lines.append(f"{key}: {_flow(value)}")
    return "".join(line + "\n" for line in lines)


def render(meta, body):
    """Ricompone una pagina: frontmatter + corpo."""
    return "---\n" + dump(meta) + "---\n" + body


def _flow(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_flow(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {_flow(v)}" for k, v in value.items()) + "}"
    return _string(str(value))


def _string(text):
    if not _needs_quotes(text):
        return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
    return f'"{escaped}"'


def _needs_quotes(text):
    if text in _RESERVED or text != text.strip():
        return True
    if _INT.match(text) or _FLOAT.match(text):
        return True
    if text[0] in "[]{}\"'#&*!|>%@`,?:-":
        return True
    return any(c in text for c in ",[]{}\n\t") or ": " in text or " #" in text
```

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -p 'test_frontmatter.py' -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core/frontmatter.py tests/test_frontmatter.py
git commit -m "feat(toolkit): restricted YAML frontmatter parser and serializer"
```

---

### Task 3: Modello della wiki (nomi, wikilink, schema, pagine)

**Files:**
- Create: `toolkit/sb_core/names.py`, `toolkit/sb_core/links.py`, `toolkit/sb_core/wiki.py`
- Modify: `toolkit/sb_core/cli.py` (`cmd_version` riporta la wiki corrente)
- Modify: `tests/helpers.py` (aggiunge `BASE_SCHEMA`, `md`, `WikiCase`)
- Test: `tests/test_wiki.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `frontmatter.parse`, `errors.WikiError`, `errors.FrontmatterError`, `FORMAT_VERSION`
- Produces:
  - `names.norm(name) -> str` (spazi compressi + casefold); `names.fold(name) -> str` (norm + rimozione accenti); `names.title_problem(title) -> str | None`; `names.FORBIDDEN_TITLE_CHARS`.
  - `links.Link(target, heading, display)` (namedtuple); `links.WIKILINK` (regex); `links.parse_link(inner) -> Link`; `links.find_links(text) -> list[Link]`; `links.links_in_value(value) -> list[Link]`; `links.page_links(page) -> list[Link]`; `links.link_target_name(value) -> str | None`.
  - `wiki.Wiki(path)` con `.root: Path`, `.version: int`, `.types: dict[str, TypeDef]`, `.thresholds: dict[str, int]`, `.sources: dict[str, dict]`, `.pages() -> list[Page]`, `.page(rel) -> Page | None`, `.lookup(name) -> (match, list[Page])` dove match ∈ `"stem"`, `"alias"`, `None`, `.invalidate()`.
  - `wiki.TypeDef(name, layer, folder, fields, required, builtin)`; `wiki.Page(path, meta, body, error)` con proprietà `.stem`, `.type`, `.title`, `.aliases`.
  - `wiki.find_root(start) -> Path`; `wiki.load_types(schema_dir) -> dict[str, TypeDef]`; `wiki.parse_date(value) -> date | None`; `wiki.closed_statuses(typedef) -> tuple`; `wiki.is_open(page, typedef) -> bool`.
  - Costanti `wiki.PAGE_ROOTS`, `wiki.LAYER_ORDER`, `wiki.SYSTEM_TYPES`, `wiki.COMMON_FIELDS`, `wiki.KINDS`, `wiki.DEFAULT_THRESHOLDS`, `wiki.DEFAULT_CLOSED`, `wiki.DEFAULT_SOURCE_STALE_DAYS`, `wiki.BUILTIN_TYPES`.
  - Helper di test: `helpers.md(meta, body="") -> str`, `helpers.BASE_SCHEMA: dict[str, str]`, `helpers.WikiCase.make_wiki(files=None, base=True) -> Path`.

- [ ] **Step 1: Estendi gli helper e scrivi i test che falliscono**

Aggiungi in fondo a `tests/helpers.py`:

```python
import shutil
import tempfile
import unittest


def md(meta, body=""):
    """Testo di una pagina a partire dalle righe di frontmatter."""
    return "---\n" + meta.strip("\n") + "\n---\n" + body


BASE_SCHEMA = {
    "schema/VERSION": "1\n",
    "schema/layers.md": md("stale_operations_days: 30\none_on_one_gap_days: 21\ndue_soon_days: 7", "# Layer\n"),
    "schema/sources.md": md(
        "sources:\n"
        "  conf-eng: {system: confluence, scope: ENG, covers: [process], stale_after_days: 30}\n"
        "  jira-plat: {system: jira, scope: PLAT, covers: [project], stale_after_days: 14}",
        "# Sorgenti\n",
    ),
    "schema/types/person.md": md(
        "name: person\nlayer: knowledge\nfolder: knowledge/people\n"
        "fields:\n  role: {kind: string}\n  team: {kind: link, to: team}",
        "# Person\n",
    ),
    "schema/types/team.md": md("name: team\nlayer: knowledge\nfolder: knowledge/teams", "# Team\n"),
    "schema/types/project.md": md(
        "name: project\nlayer: knowledge\nfolder: knowledge/projects\n"
        "fields:\n  status: {kind: enum, values: [active, paused, closed]}",
        "# Project\n",
    ),
    "schema/types/topic.md": md("name: topic\nlayer: knowledge\nfolder: knowledge/topics", "# Topic\n"),
    "schema/types/vendor.md": md("name: vendor\nlayer: knowledge\nfolder: knowledge/vendors", "# Vendor\n"),
    "schema/types/source-note.md": md("name: source-note\nlayer: knowledge\nfolder: knowledge/sources", "# Source note\n"),
    "schema/types/task.md": md(
        "name: task\nlayer: operations\nfolder: operations/tasks\nfields:\n"
        "  status: {kind: enum, values: [todo, doing, blocked, done, dropped], closed: [done, dropped]}\n"
        "  owner: {kind: link, to: person}\n  due: {kind: date}\n"
        "  priority: {kind: enum, values: [low, medium, high]}\n  related: {kind: list, of: link}",
        "# Task\n",
    ),
    "schema/types/one-on-one.md": md(
        "name: one-on-one\nlayer: operations\nfolder: operations/one-on-ones\n"
        "fields:\n  with: {kind: link, to: person}\n  date: {kind: date}\nrequired: [with, date]",
        "# One-on-one\n",
    ),
    "schema/types/risk.md": md(
        "name: risk\nlayer: operations\nfolder: operations/risks\n"
        "fields:\n  status: {kind: enum, values: [open, mitigating, closed, accepted], closed: [closed, accepted]}",
        "# Risk\n",
    ),
}


class WikiCase(unittest.TestCase):
    """TestCase con una wiki temporanea costruita da un dizionario path → contenuto."""

    def make_wiki(self, files=None, base=True):
        tmp = Path(tempfile.mkdtemp(prefix="sb-test-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        everything = dict(BASE_SCHEMA) if base else {}
        everything.update(files or {})
        for rel, content in everything.items():
            path = tmp / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return tmp
```

`tests/test_wiki.py`:

```python
import unittest

from helpers import WikiCase, md
from sb_core.errors import WikiError
from sb_core.links import find_links, link_target_name, parse_link
from sb_core.names import fold, norm, title_problem
from sb_core.wiki import Wiki, is_open, parse_date


class NamesTest(unittest.TestCase):
    def test_norm_and_fold(self):
        self.assertEqual(norm("  Luca   BIANCHI "), "luca bianchi")
        self.assertEqual(fold("Nicolò Ågren"), "nicolo agren")

    def test_title_problem(self):
        self.assertIsNone(title_problem("2026-10-02 1on1 Luca"))
        self.assertIn(":", title_problem("1:1 Luca"))
        self.assertIsNotNone(title_problem(" Luca"))
        self.assertIsNotNone(title_problem(""))
        self.assertIsNotNone(title_problem(".nascosto"))
        self.assertIsNotNone(title_problem(42))


class LinksTest(unittest.TestCase):
    def test_parse_link(self):
        self.assertEqual(tuple(parse_link("Luca Bianchi")), ("Luca Bianchi", None, None))
        self.assertEqual(tuple(parse_link("people/Luca Bianchi.md#Note|Luca")), ("Luca Bianchi", "Note", "Luca"))
        self.assertEqual(parse_link("#sezione").target, "")

    def test_find_links_ignores_footnotes(self):
        text = "Vedi [[A]] e [[B|bi]]. Fonte ^[raw/2026/10/x] e [link](http://x)."
        self.assertEqual([l.target for l in find_links(text)], ["A", "B"])

    def test_link_target_name(self):
        self.assertEqual(link_target_name("[[Luca Bianchi|Luca]]"), "Luca Bianchi")
        self.assertEqual(link_target_name("Luca"), "Luca")
        self.assertIsNone(link_target_name(None))
        self.assertIsNone(link_target_name("  "))


class WikiTest(WikiCase):
    def test_loads_schema(self):
        wiki = Wiki(self.make_wiki())
        self.assertEqual(wiki.types["person"].folder, "knowledge/people")
        self.assertEqual(wiki.types["person"].layer, "knowledge")
        self.assertTrue(wiki.types["briefing"].builtin)
        self.assertEqual(wiki.types["report"].folder, "outputs/reports")
        self.assertEqual(wiki.thresholds, {"stale_operations_days": 30, "one_on_one_gap_days": 21, "due_soon_days": 7})
        self.assertEqual(wiki.sources["conf-eng"]["system"], "confluence")
        self.assertEqual(wiki.types["one-on-one"].required, ["with", "date"])

    def test_not_a_wiki(self):
        root = self.make_wiki(base=False)
        with self.assertRaises(WikiError):
            Wiki(root)

    def test_finds_root_from_subfolder(self):
        root = self.make_wiki({"knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi")})
        self.assertEqual(Wiki(root / "knowledge" / "people").root, root.resolve())

    def test_format_version_checks(self):
        for version in ("2\n", "0\n", "uno\n"):
            with self.subTest(version=version):
                with self.assertRaises(WikiError):
                    Wiki(self.make_wiki({"schema/VERSION": version}))

    def test_missing_system_type(self):
        root = self.make_wiki()
        (root / "schema" / "types" / "task.md").unlink()
        with self.assertRaisesRegex(WikiError, "task"):
            Wiki(root)

    def test_invalid_type_definitions(self):
        cases = {
            "layer": md("name: x\nlayer: other\nfolder: other/x"),
            "folder": md("name: x\nlayer: knowledge\nfolder: operations/x"),
            "kind": md("name: x\nlayer: knowledge\nfolder: knowledge/x\nfields:\n  a: {kind: colore}"),
            "enum": md("name: x\nlayer: knowledge\nfolder: knowledge/x\nfields:\n  a: {kind: enum}"),
        }
        for label, text in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(WikiError):
                    Wiki(self.make_wiki({"schema/types/x.md": text}))

    def test_pages_and_lookup(self):
        root = self.make_wiki({
            "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi\naliases: [Luca, LB]"),
            "operations/tasks/Rotto.md": "---\ntitle: [\n---\n",
            "raw/2026/10/x.md": "grezzo",
            "index.md": "# Indice\n",
        })
        wiki = Wiki(root)
        self.assertEqual([p.path for p in wiki.pages()], ["knowledge/people/Luca Bianchi.md", "operations/tasks/Rotto.md"])
        broken = wiki.page("operations/tasks/Rotto.md")
        self.assertIsNone(broken.meta)
        self.assertTrue(broken.error)
        self.assertEqual(wiki.lookup("luca bianchi")[0], "stem")
        match, pages = wiki.lookup("LB")
        self.assertEqual((match, pages[0].title), ("alias", "Luca Bianchi"))
        self.assertEqual(wiki.lookup("Nessuno"), (None, []))

    def test_parse_date(self):
        self.assertEqual(parse_date("2026-10-02").isoformat(), "2026-10-02")
        self.assertIsNone(parse_date("venerdì"))
        self.assertIsNone(parse_date(None))

    def test_is_open(self):
        root = self.make_wiki({
            "operations/tasks/A.md": md("type: task\ntitle: A"),
            "operations/tasks/B.md": md("type: task\ntitle: B\nstatus: done"),
            "operations/risks/R.md": md("type: risk\ntitle: R\nstatus: accepted"),
            "operations/risks/S.md": md("type: risk\ntitle: S\nstatus: open"),
        })
        wiki = Wiki(root)
        result = {p.title: is_open(p, wiki.types[p.type]) for p in wiki.pages()}
        self.assertEqual(result, {"A": True, "B": False, "R": False, "S": True})


if __name__ == "__main__":
    unittest.main()
```

Aggiungi a `tests/test_cli.py`, dentro `CliTest`. Serve anche importare `WikiCase` e far ereditare la classe da `WikiCase`: sostituisci `class CliTest(unittest.TestCase):` con `class CliTest(WikiCase):` e la riga di import con `from helpers import ROOT, WikiCase, run_cli`.

```python
    def test_version_reports_current_wiki(self):
        root = self.make_wiki()
        code, data, _ = run_cli("version", "--wiki", root)
        self.assertEqual(code, 0)
        self.assertEqual(data["wiki"], str(root.resolve()))
        code, data, _ = run_cli("version", "--wiki", self.make_wiki(base=False))
        self.assertIsNone(data["wiki"])
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -v`
Expected: ERROR `No module named 'sb_core.links'` (e analoghi)

- [ ] **Step 3: Implementa i moduli**

`toolkit/sb_core/names.py`:

```python
"""Normalizzazione dei nomi e regole sui titoli (titolo = nome del file)."""
import unicodedata

FORBIDDEN_TITLE_CHARS = '\\/:*?"<>|#^[]'


def norm(name):
    """Confronto case-insensitive con spazi compressi, come fa Obsidian sui nomi file."""
    return " ".join(str(name).split()).casefold()


def fold(name):
    """norm + rimozione degli accenti, per i confronti approssimati."""
    decomposed = unicodedata.normalize("NFKD", norm(name))
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def title_problem(title):
    """Motivo per cui il titolo non può essere un nome file, oppure None se va bene."""
    if not isinstance(title, str) or not title.strip():
        return "titolo vuoto o non testuale"
    if title != title.strip():
        return "il titolo ha spazi iniziali o finali"
    if title.startswith("."):
        return "il titolo non può iniziare con '.'"
    bad = sorted({c for c in title if c in FORBIDDEN_TITLE_CHARS})
    if bad:
        return "caratteri non ammessi nel titolo: " + " ".join(bad)
    return None
```

`toolkit/sb_core/links.py`:

```python
"""Wikilink in stile Obsidian: [[Titolo]], [[Titolo#sezione]], [[Titolo|testo]]."""
import re
from collections import namedtuple

WIKILINK = re.compile(r"\[\[([^\[\]\n]+?)\]\]")

Link = namedtuple("Link", "target heading display")


def parse_link(inner):
    target, _, display = inner.partition("|")
    target, _, heading = target.partition("#")
    target = target.strip().rsplit("/", 1)[-1]
    if target.lower().endswith(".md"):
        target = target[:-3]
    return Link(target.strip(), heading.strip() or None, display.strip() or None)


def find_links(text):
    return [parse_link(m.group(1)) for m in WIKILINK.finditer(text or "")]


def links_in_value(value):
    """Wikilink contenuti in un valore di frontmatter (stringa, lista o mappa)."""
    if isinstance(value, str):
        return find_links(value)
    if isinstance(value, list):
        return [link for item in value for link in links_in_value(item)]
    if isinstance(value, dict):
        return [link for item in value.values() for link in links_in_value(item)]
    return []


def page_links(page):
    """Tutti i wikilink di una pagina: frontmatter + corpo."""
    return links_in_value(page.meta or {}) + find_links(page.body)


def link_target_name(value):
    """Nome del target per un valore come "[[Luca|L]]"; testo semplice ripulito; None se vuoto."""
    if not isinstance(value, str):
        return None
    links = find_links(value)
    if links:
        return links[0].target or None
    return value.strip() or None
```

`toolkit/sb_core/wiki.py`:

```python
"""Modello della wiki: radice, schema (tipi, soglie, sorgenti) e pagine."""
import datetime
from pathlib import Path

from . import FORMAT_VERSION
from .errors import FrontmatterError, WikiError
from .frontmatter import parse
from .names import norm

PAGE_ROOTS = ("knowledge", "operations", "outputs")
LAYER_ORDER = ("knowledge", "operations", "outputs")
SYSTEM_TYPES = ("task", "source-note")
COMMON_FIELDS = (
    "type", "title", "aliases", "created", "updated", "sources",
    "external", "version", "synced", "authority",
)
KINDS = ("string", "text", "date", "number", "bool", "enum", "link", "list")
DEFAULT_THRESHOLDS = {"stale_operations_days": 30, "one_on_one_gap_days": 21, "due_soon_days": 7}
DEFAULT_CLOSED = ("done", "dropped")
DEFAULT_SOURCE_STALE_DAYS = 30


class TypeDef(object):
    def __init__(self, name, layer, folder, fields=None, required=None, builtin=False):
        self.name = name
        self.layer = layer
        self.folder = folder
        self.fields = fields or {}
        self.required = list(required or [])
        self.builtin = builtin


BUILTIN_TYPES = (
    TypeDef("briefing", "outputs", "outputs/briefings",
            {"about": {"kind": "link"}, "for": {"kind": "date"}}, builtin=True),
    TypeDef("report", "outputs", "outputs/reports",
            {"kind": {"kind": "string"}, "scope": {"kind": "string"}, "period": {"kind": "string"}}, builtin=True),
)


class Page(object):
    def __init__(self, path, meta, body, error=None):
        self.path = path      # relativo alla radice della wiki, separatore '/'
        self.meta = meta      # dict, oppure None se il frontmatter manca o è illeggibile
        self.body = body
        self.error = error    # messaggio d'errore del frontmatter, se illeggibile

    @property
    def stem(self):
        return self.path.rsplit("/", 1)[-1][:-3]

    @property
    def type(self):
        return (self.meta or {}).get("type")

    @property
    def title(self):
        title = (self.meta or {}).get("title")
        return title if isinstance(title, str) else self.stem

    @property
    def aliases(self):
        aliases = (self.meta or {}).get("aliases")
        if not isinstance(aliases, list):
            return []
        return [a for a in aliases if isinstance(a, str)]


def parse_date(value):
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def closed_statuses(typedef):
    spec = typedef.fields.get("status") if typedef is not None else None
    closed = spec.get("closed") if isinstance(spec, dict) else None
    return tuple(closed) if isinstance(closed, list) else DEFAULT_CLOSED


def is_open(page, typedef):
    """Un item è aperto se il suo status non è tra quelli chiusi. Un task senza status è 'todo'."""
    status = (page.meta or {}).get("status")
    if status is None:
        return page.type == "task"
    return status not in closed_statuses(typedef)


def find_root(start):
    path = Path(start).resolve()
    for candidate in [path] + list(path.parents):
        if (candidate / "schema" / "VERSION").is_file():
            return candidate
    raise WikiError(f"{path} non è dentro una wiki second-brain (manca schema/VERSION)")


def _read_meta(path):
    try:
        meta, _ = parse(path.read_text(encoding="utf-8"))
    except FrontmatterError as exc:
        raise WikiError(f"{path.name}: {exc}")
    return meta or {}


def load_types(schema_dir):
    """Carica e controlla schema/types/*.md. Aggiunge i tipi predefiniti."""
    types_dir = Path(schema_dir) / "types"
    if not types_dir.is_dir():
        raise WikiError(f"manca la cartella {types_dir}")
    types = {}
    for path in sorted(types_dir.glob("*.md")):
        meta = _read_meta(path)
        name, layer, folder = meta.get("name"), meta.get("layer"), meta.get("folder")
        if not (isinstance(name, str) and name and isinstance(folder, str) and folder):
            raise WikiError(f"{path.name}: 'name' e 'folder' sono obbligatori")
        if layer not in ("knowledge", "operations"):
            raise WikiError(f"{path.name}: 'layer' deve essere knowledge o operations")
        if not folder.startswith(layer + "/"):
            raise WikiError(f"{path.name}: 'folder' deve stare sotto {layer}/")
        fields = meta.get("fields") or {}
        if not isinstance(fields, dict) or not all(isinstance(v, dict) for v in fields.values()):
            raise WikiError(f"{path.name}: 'fields' deve associare ogni campo a {{kind: ...}}")
        for field, spec in fields.items():
            kind = spec.get("kind")
            if kind not in KINDS:
                raise WikiError(f"{path.name}: campo '{field}' ha kind '{kind}' non valido ({', '.join(KINDS)})")
            if kind == "enum" and not isinstance(spec.get("values"), list):
                raise WikiError(f"{path.name}: il campo enum '{field}' richiede 'values: [...]'")
            if kind == "list" and spec.get("of") not in (None,) + KINDS[:-1]:
                raise WikiError(f"{path.name}: 'of' del campo '{field}' non valido")
        required = meta.get("required") or []
        if not isinstance(required, list):
            raise WikiError(f"{path.name}: 'required' deve essere una lista")
        if name in types:
            raise WikiError(f"tipo duplicato: {name}")
        types[name] = TypeDef(name, layer, folder, fields, required)
    missing = [t for t in SYSTEM_TYPES if t not in types]
    if missing:
        raise WikiError("mancano i tipi di sistema: " + ", ".join(missing))
    for builtin in BUILTIN_TYPES:
        types.setdefault(builtin.name, builtin)
    return types


def _load_thresholds(schema_dir):
    thresholds = dict(DEFAULT_THRESHOLDS)
    path = schema_dir / "layers.md"
    if path.is_file():
        meta = _read_meta(path)
        for key in thresholds:
            if isinstance(meta.get(key), int) and not isinstance(meta.get(key), bool):
                thresholds[key] = meta[key]
    return thresholds


def _load_sources(schema_dir):
    path = schema_dir / "sources.md"
    if not path.is_file():
        return {}
    sources = _read_meta(path).get("sources") or {}
    if not isinstance(sources, dict) or not all(
        isinstance(e, dict) and isinstance(e.get("system"), str) for e in sources.values()
    ):
        raise WikiError("schema/sources.md: 'sources' deve associare ogni id a {system: ..., ...}")
    return sources


class Wiki(object):
    def __init__(self, path):
        self.root = find_root(path)
        schema_dir = self.root / "schema"
        raw_version = (schema_dir / "VERSION").read_text(encoding="utf-8").strip()
        try:
            self.version = int(raw_version)
        except ValueError:
            raise WikiError("schema/VERSION non contiene un numero")
        if self.version > FORMAT_VERSION:
            raise WikiError(f"wiki in formato {self.version}, il toolkit supporta fino al {FORMAT_VERSION}: aggiorna il plugin")
        if self.version < FORMAT_VERSION:
            raise WikiError(f"wiki in formato {self.version}: serve una migrazione di formato al {FORMAT_VERSION}")
        self.types = load_types(schema_dir)
        self.thresholds = _load_thresholds(schema_dir)
        self.sources = _load_sources(schema_dir)
        self.invalidate()

    def invalidate(self):
        """Dimentica le pagine lette: da chiamare dopo aver scritto su disco."""
        self._pages = None
        self._by_path = None
        self._by_stem = None
        self._by_alias = None

    def pages(self):
        if self._pages is None:
            pages = []
            for root_name in PAGE_ROOTS:
                base = self.root / root_name
                if not base.is_dir():
                    continue
                for path in sorted(base.rglob("*.md")):
                    rel = path.relative_to(self.root).as_posix()
                    try:
                        text = path.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        pages.append(Page(rel, None, "", "il file non è UTF-8"))
                        continue
                    try:
                        meta, body = parse(text)
                    except FrontmatterError as exc:
                        pages.append(Page(rel, None, text, str(exc)))
                        continue
                    pages.append(Page(rel, meta, body))
            self._pages = pages
        return self._pages

    def _build_indexes(self):
        if self._by_stem is not None:
            return
        by_path, by_stem, by_alias = {}, {}, {}
        for page in self.pages():
            by_path[page.path] = page
            by_stem.setdefault(norm(page.stem), []).append(page)
            for alias in page.aliases:
                by_alias.setdefault(norm(alias), []).append(page)
        self._by_path, self._by_stem, self._by_alias = by_path, by_stem, by_alias

    def page(self, rel):
        self._build_indexes()
        return self._by_path.get(rel)

    def lookup(self, name):
        """Risolve il target di un wikilink come Obsidian (nome file), poi per alias."""
        self._build_indexes()
        key = norm(name)
        if key in self._by_stem:
            return "stem", self._by_stem[key]
        if key in self._by_alias:
            return "alias", self._by_alias[key]
        return None, []
```

In `toolkit/sb_core/cli.py` sostituisci `cmd_version` e aggiungi l'import:

```python
from .wiki import Wiki, find_root
```

```python
def cmd_version(args):
    try:
        root = str(find_root(args.wiki))
    except SbError:
        root = None
    return {"toolkit": __version__, "format": FORMAT_VERSION, "wiki": root}, 0


def _wiki(args):
    return Wiki(args.wiki)
```

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core tests
git commit -m "feat(toolkit): wiki model with schema loading, pages and wikilink lookup"
```

---

### Task 4: `validate`

**Files:**
- Create: `toolkit/sb_core/validate.py`
- Modify: `toolkit/sb_core/cli.py` (comando `validate`)
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `Wiki`, `Page`, `COMMON_FIELDS`, `parse_date`, `find_links`, `norm`, `title_problem`, `WikiError`
- Produces: `validate.Issue(path, code, message, severity="error")` con `.to_dict() -> {"path","severity","code","message"}`; `validate.validate(wiki, paths=None) -> list[Issue]`; `validate.validate_page(wiki, page) -> list[Issue]`. Codici: `no-frontmatter`, `bad-frontmatter`, `missing-type`, `unknown-type`, `missing-title`, `bad-title`, `filename-mismatch`, `wrong-folder`, `duplicate-title`, `missing-required`, `bad-value`, `unknown-field` (warning), `broken-link`, `wrong-link-type`, `alias-link` (warning), `unknown-source`. CLI: `sb validate [paths…]` → `{"ok": bool, "checked": int, "issues": [...]}`, exit 1 se c'è almeno un errore.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_validate.py`:

```python
import unittest
from collections import Counter

from helpers import WikiCase, md, run_cli
from sb_core.errors import WikiError
from sb_core.validate import validate
from sb_core.wiki import Wiki

GOOD = {
    "knowledge/people/Luca Bianchi.md": md(
        'type: person\ntitle: Luca Bianchi\naliases: [Luca]\nteam: "[[Platform]]"', "Lavora con [[Platform]].\n"
    ),
    "knowledge/teams/Platform.md": md("type: team\ntitle: Platform"),
    "operations/tasks/Chiedere la stima.md": md(
        'type: task\ntitle: Chiedere la stima\nstatus: todo\nowner: "[[Luca Bianchi|Luca]]"\n'
        'due: 2026-10-09\nrelated: ["[[Platform]]"]\ncreated: 2026-10-02'
    ),
}


class ValidateTest(WikiCase):
    def codes(self, files, paths=None):
        wiki = Wiki(self.make_wiki(files))
        return Counter((i.path, i.code) for i in validate(wiki, paths))

    def test_valid_wiki(self):
        self.assertEqual(self.codes(GOOD), Counter())

    def test_frontmatter_problems(self):
        self.assertEqual(self.codes({
            "knowledge/people/A.md": "senza frontmatter",
            "knowledge/people/B.md": "---\ntitle: [\n---\n",
        }), Counter({("knowledge/people/A.md", "no-frontmatter"): 1, ("knowledge/people/B.md", "bad-frontmatter"): 1}))

    def test_type_title_and_folder(self):
        self.assertEqual(self.codes({
            "knowledge/people/X.md": md("title: X"),
            "knowledge/people/Y.md": md("type: martian\ntitle: Y"),
            "knowledge/people/Z.md": md("type: person"),
            "knowledge/people/W.md": md("type: person\ntitle: Altro nome"),
            "knowledge/teams/V.md": md("type: person\ntitle: V"),
            "knowledge/people/K.md": md('type: person\ntitle: "K: x"'),
        }), Counter({
            ("knowledge/people/X.md", "missing-type"): 1,
            ("knowledge/people/Y.md", "unknown-type"): 1,
            ("knowledge/people/Z.md", "missing-title"): 1,
            ("knowledge/people/W.md", "filename-mismatch"): 1,
            ("knowledge/teams/V.md", "wrong-folder"): 1,
            ("knowledge/people/K.md", "bad-title"): 1,
        }))

    def test_field_values(self):
        files = dict(GOOD)
        files["operations/tasks/T.md"] = md(
            'type: task\ntitle: T\nstatus: wip\ndue: venerdì\npriority: urgent\n'
            'owner: Luca Bianchi\nrelated: "[[Platform]]"\nestimate: 3'
        )
        self.assertEqual(self.codes(files), Counter({
            ("operations/tasks/T.md", "bad-value"): 5,
            ("operations/tasks/T.md", "unknown-field"): 1,
        }))

    def test_links(self):
        files = dict(GOOD)
        files["operations/tasks/T.md"] = md(
            'type: task\ntitle: T\nowner: "[[Platform]]"\nrelated: ["[[Nessuno]]"]',
            "Vedi [[Luca]], [[Fantasma]] e [[#sezione]].\n",
        )
        self.assertEqual(self.codes(files), Counter({
            ("operations/tasks/T.md", "wrong-link-type"): 1,
            ("operations/tasks/T.md", "broken-link"): 2,
            ("operations/tasks/T.md", "alias-link"): 1,
        }))

    def test_duplicate_titles_are_case_insensitive(self):
        self.assertEqual(self.codes({
            "knowledge/people/Luca.md": md("type: person\ntitle: Luca"),
            "knowledge/teams/luca.md": md("type: team\ntitle: luca"),
        }), Counter({
            ("knowledge/people/Luca.md", "duplicate-title"): 1,
            ("knowledge/teams/luca.md", "duplicate-title"): 1,
        }))

    def test_common_fields(self):
        self.assertEqual(self.codes({
            "knowledge/sources/S.md": md(
                'type: source-note\ntitle: S\nexternal: "notion:abc"\nsynced: ieri\nauthority: external\naliases: Luca'
            ),
            "knowledge/sources/T.md": md('type: source-note\ntitle: T\nexternal: "confluence:ENG/1"\nsynced: 2026-10-01'),
            "knowledge/sources/U.md": md('type: source-note\ntitle: U\nexternal: "url:https://example.com/a"'),
        }), Counter({
            ("knowledge/sources/S.md", "unknown-source"): 1,
            ("knowledge/sources/S.md", "bad-value"): 3,
        }))

    def test_required_fields(self):
        self.assertEqual(self.codes({"operations/one-on-ones/O.md": md("type: one-on-one\ntitle: O")}),
                         Counter({("operations/one-on-ones/O.md", "missing-required"): 2}))

    def test_paths_filter(self):
        files = dict(GOOD)
        files["knowledge/people/X.md"] = md("title: X")
        self.assertEqual(self.codes(files, ["knowledge/teams/Platform.md"]), Counter())
        wiki = Wiki(self.make_wiki(GOOD))
        with self.assertRaises(WikiError):
            validate(wiki, ["knowledge/people/Nessuno.md"])

    def test_cli(self):
        root = self.make_wiki(GOOD)
        code, data, _ = run_cli("validate", "--wiki", root)
        self.assertEqual((code, data["ok"], data["checked"]), (0, True, 3))
        (root / "knowledge" / "people" / "X.md").write_text(md("title: X"), encoding="utf-8")
        code, data, _ = run_cli("validate", "--wiki", root)
        self.assertEqual((code, data["ok"]), (1, False))
        self.assertEqual(data["issues"][0]["code"], "missing-type")
        code, data, _ = run_cli("validate", "--wiki", root, str(root / "knowledge" / "teams" / "Platform.md"))
        self.assertEqual((code, data["checked"]), (0, 1))
        code, data, _ = run_cli("validate", "--wiki", self.make_wiki(base=False))
        self.assertEqual(code, 2)
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_validate.py' -v`
Expected: ERROR `No module named 'sb_core.validate'`

- [ ] **Step 3: Implementa**

`toolkit/sb_core/validate.py`:

```python
"""Validazione delle pagine contro lo schema della wiki."""
import re
from pathlib import Path

from .errors import WikiError
from .links import find_links
from .names import norm, title_problem
from .wiki import COMMON_FIELDS, parse_date

_LINK_VALUE = re.compile(r"^\[\[[^\[\]]+\]\]$")
ALWAYS_ALLOWED_SYSTEMS = ("url", "mail")
AUTHORITY_VALUES = ("migrated",)


class Issue(object):
    def __init__(self, path, code, message, severity="error"):
        self.path = path
        self.code = code
        self.message = message
        self.severity = severity

    def to_dict(self):
        return {"path": self.path, "severity": self.severity, "code": self.code, "message": self.message}


def validate(wiki, paths=None):
    selected = _select(wiki, paths)
    issues = _duplicate_titles(wiki, selected)
    for page in selected:
        issues.extend(validate_page(wiki, page))
    return issues


def _relative(wiki, raw):
    path = Path(raw)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(wiki.root).as_posix()
        except ValueError:
            raise WikiError(f"{raw} è fuori dalla wiki")
    text = path.as_posix()
    return text[2:] if text.startswith("./") else text


def _select(wiki, paths):
    pages = wiki.pages()
    if not paths:
        return list(pages)
    wanted = {_relative(wiki, p) for p in paths}
    unknown = wanted - {p.path for p in pages}
    if unknown:
        raise WikiError("pagine non trovate: " + ", ".join(sorted(unknown)))
    return [p for p in pages if p.path in wanted]


def _duplicate_titles(wiki, selected):
    groups = {}
    for page in wiki.pages():
        groups.setdefault(norm(page.stem), []).append(page)
    selected_paths = {p.path for p in selected}
    issues = []
    for group in groups.values():
        if len(group) < 2:
            continue
        for page in group:
            if page.path in selected_paths:
                others = ", ".join(p.path for p in group if p is not page)
                issues.append(Issue(page.path, "duplicate-title", f"stesso nome di {others}: i wikilink sono ambigui"))
    return issues


def validate_page(wiki, page):
    if page.error:
        return [Issue(page.path, "bad-frontmatter", page.error)]
    if page.meta is None:
        return [Issue(page.path, "no-frontmatter", "manca il frontmatter")]
    meta = page.meta
    issues = []
    type_name = meta.get("type")
    title = meta.get("title")
    if not type_name:
        issues.append(Issue(page.path, "missing-type", "manca il campo 'type'"))
    if title is None:
        issues.append(Issue(page.path, "missing-title", "manca il campo 'title'"))
    else:
        problem = title_problem(title)
        if problem:
            issues.append(Issue(page.path, "bad-title", problem))
        elif title != page.stem:
            issues.append(Issue(page.path, "filename-mismatch", f"il nome del file deve essere '{title}.md'"))
    typedef = wiki.types.get(type_name) if type_name else None
    if type_name and typedef is None:
        issues.append(Issue(page.path, "unknown-type", f"tipo '{type_name}' non definito in schema/types"))
    if typedef is not None:
        folder = page.path.rsplit("/", 1)[0]
        if folder != typedef.folder:
            issues.append(Issue(page.path, "wrong-folder", f"le pagine di tipo '{typedef.name}' stanno in {typedef.folder}/"))
        for field in typedef.required:
            if meta.get(field) in (None, "", []):
                issues.append(Issue(page.path, "missing-required", f"campo obbligatorio mancante: {field}"))
        for field, value in meta.items():
            if field in COMMON_FIELDS or value is None:
                continue
            spec = typedef.fields.get(field)
            if spec is None:
                issues.append(Issue(page.path, "unknown-field",
                                    f"campo '{field}' non previsto dal tipo '{typedef.name}'", "warning"))
                continue
            issues.extend(_check_value(wiki, page.path, field, value, spec))
    issues.extend(_check_common(wiki, page))
    issues.extend(_check_body_links(wiki, page))
    return issues


def _check_value(wiki, path, field, value, spec):
    kind = spec.get("kind")
    if kind == "list":
        if not isinstance(value, list):
            return [Issue(path, "bad-value", f"'{field}' deve essere una lista")]
        item_kind = spec.get("of")
        if not item_kind:
            return []
        item_spec = dict(spec, kind=item_kind)
        issues = []
        for item in value:
            issues.extend(_check_value(wiki, path, field, item, item_spec))
        return issues
    problem = _kind_problem(kind, value, spec)
    if problem:
        return [Issue(path, "bad-value", f"'{field}': {problem}")]
    if kind == "link":
        return _check_link_value(wiki, path, field, value, spec.get("to"))
    return []


def _kind_problem(kind, value, spec):
    if kind in ("string", "text"):
        return None if isinstance(value, str) else "atteso un testo"
    if kind == "date":
        return None if parse_date(value) else "attesa una data AAAA-MM-GG"
    if kind == "number":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        return None if ok else "atteso un numero"
    if kind == "bool":
        return None if isinstance(value, bool) else "atteso true o false"
    if kind == "enum":
        values = spec.get("values") or []
        return None if value in values else f"valore '{value}' non ammesso ({', '.join(map(str, values))})"
    if kind == "link":
        ok = isinstance(value, str) and _LINK_VALUE.match(value.strip())
        return None if ok else 'atteso un wikilink "[[Titolo]]"'
    return None


def _alias_issue(path, link, targets):
    canonical = targets[0].stem
    return Issue(path, "alias-link", f"[[{link.target}]] è un alias: usa [[{canonical}|{link.target}]]", "warning")


def _check_link_value(wiki, path, field, value, to_type):
    link = find_links(value)[0]
    match, targets = wiki.lookup(link.target)
    if not targets:
        return [Issue(path, "broken-link", f"'{field}' punta a [[{link.target}]], che non esiste")]
    issues = []
    if match == "alias":
        issues.append(_alias_issue(path, link, targets))
    if to_type and len(targets) == 1 and targets[0].type != to_type:
        issues.append(Issue(path, "wrong-link-type",
                            f"'{field}' deve puntare a una pagina di tipo '{to_type}': "
                            f"[[{link.target}]] è di tipo '{targets[0].type}'"))
    return issues


def _check_common(wiki, page):
    meta, path = page.meta, page.path
    issues = []
    for field in ("created", "updated", "synced"):
        if meta.get(field) is not None and parse_date(meta[field]) is None:
            issues.append(Issue(path, "bad-value", f"'{field}': attesa una data AAAA-MM-GG"))
    for field in ("aliases", "sources"):
        value = meta.get(field)
        if value is not None and not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
            issues.append(Issue(path, "bad-value", f"'{field}' deve essere una lista di testi"))
    if meta.get("external") is not None:
        issues.extend(_check_external(wiki, path, meta["external"]))
    authority = meta.get("authority")
    if authority is not None and authority not in AUTHORITY_VALUES:
        issues.append(Issue(path, "bad-value", "'authority' ammette solo: " + ", ".join(AUTHORITY_VALUES)))
    return issues


def _check_external(wiki, path, external):
    if not isinstance(external, str) or ":" not in external:
        return [Issue(path, "bad-value", "'external' deve essere '<sistema>:<riferimento>'")]
    system = external.split(":", 1)[0]
    known = set(ALWAYS_ALLOWED_SYSTEMS) | {entry.get("system") for entry in wiki.sources.values()}
    if system not in known:
        return [Issue(path, "unknown-source", f"sistema '{system}' non registrato in schema/sources.md")]
    return []


def _check_body_links(wiki, page):
    issues = []
    for link in find_links(page.body):
        if not link.target:
            continue
        match, targets = wiki.lookup(link.target)
        if not targets:
            issues.append(Issue(page.path, "broken-link", f"[[{link.target}]] non esiste"))
        elif match == "alias":
            issues.append(_alias_issue(page.path, link, targets))
    return issues
```

In `toolkit/sb_core/cli.py` aggiungi l'import `from .validate import validate` e, prima di `COMMANDS`:

```python
def _add_validate(sub, common):
    p = sub.add_parser("validate", parents=[common], help="valida le pagine contro lo schema")
    p.add_argument("paths", nargs="*", help="pagine da validare (default: tutte)")
    p.set_defaults(handler=cmd_validate)


def cmd_validate(args):
    wiki = _wiki(args)
    issues = validate(wiki, args.paths)
    errors = [i for i in issues if i.severity == "error"]
    checked = len(args.paths) if args.paths else len(wiki.pages())
    return {"ok": not errors, "checked": checked, "issues": [i.to_dict() for i in issues]}, 1 if errors else 0
```

Aggiorna: `COMMANDS = [_add_version, _add_validate]`

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core/validate.py toolkit/sb_core/cli.py tests/test_validate.py
git commit -m "feat(toolkit): validate pages against schema"
```

---

### Task 5: `index` e grafo dei link

**Files:**
- Create: `toolkit/sb_core/index.py`
- Modify: `toolkit/sb_core/links.py` (aggiunge `graph`), `toolkit/sb_core/cli.py` (comando `index`)
- Test: `tests/test_index.py`

**Interfaces:**
- Consumes: `Wiki.pages()`, `Wiki.lookup()`, `links.page_links`, `names.norm`, `wiki.LAYER_ORDER`
- Produces:
  - `links.graph(wiki) -> (outgoing, incoming)`: due `dict[path, set[path]]` con soli link risolti in modo univoco, senza self-link, per le pagine con frontmatter leggibile;
  - `index.build_index(wiki) -> str`;
  - `index.build_backlinks(wiki) -> dict[target_path, list[source_path]]`;
  - `index.write_index(wiki) -> {"pages": int, "index": "index.md", "backlinks": ".sb/backlinks.json"}`.
  - CLI: `sb index`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_index.py`:

```python
import json
import unittest

from helpers import WikiCase, md, run_cli
from sb_core.index import write_index
from sb_core.links import graph
from sb_core.wiki import Wiki

FILES = {
    "knowledge/people/Luca Bianchi.md": md(
        'type: person\ntitle: Luca Bianchi\nupdated: 2026-10-02\nteam: "[[Platform]]"',
        "Lavora con [[Platform]] e cita sé stesso: [[Luca Bianchi]].\n",
    ),
    "knowledge/teams/Platform.md": md("type: team\ntitle: Platform", "Link rotto: [[Fantasma]].\n"),
    "operations/tasks/Chiedere la stima.md": md(
        'type: task\ntitle: Chiedere la stima\nowner: "[[Luca Bianchi]]"\nrelated: ["[[Platform]]"]\ncreated: 2026-10-01'
    ),
}


class IndexTest(WikiCase):
    def test_index_content(self):
        root = self.make_wiki(FILES)
        result = write_index(Wiki(root))
        text = (root / "index.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Indice"))
        self.assertIn("## knowledge\n\n### person (1)\n- [[Luca Bianchi]] · 2026-10-02\n\n### team (1)\n- [[Platform]]\n", text)
        self.assertIn("## operations\n\n### task (1)\n- [[Chiedere la stima]] · 2026-10-01\n", text)
        self.assertNotIn("## outputs", text)
        self.assertEqual(result, {"pages": 3, "index": "index.md", "backlinks": ".sb/backlinks.json"})

    def test_backlinks_file(self):
        root = self.make_wiki(FILES)
        write_index(Wiki(root))
        backlinks = json.loads((root / ".sb" / "backlinks.json").read_text(encoding="utf-8"))
        self.assertEqual(backlinks, {
            "knowledge/people/Luca Bianchi.md": ["operations/tasks/Chiedere la stima.md"],
            "knowledge/teams/Platform.md": ["knowledge/people/Luca Bianchi.md", "operations/tasks/Chiedere la stima.md"],
        })

    def test_graph_ignores_self_and_broken_links(self):
        outgoing, incoming = graph(Wiki(self.make_wiki(FILES)))
        self.assertEqual(outgoing["knowledge/people/Luca Bianchi.md"], {"knowledge/teams/Platform.md"})
        self.assertEqual(outgoing["knowledge/teams/Platform.md"], set())
        self.assertEqual(incoming["operations/tasks/Chiedere la stima.md"], set())

    def test_cli(self):
        root = self.make_wiki(FILES)
        code, data, _ = run_cli("index", "--wiki", root)
        self.assertEqual((code, data["pages"]), (0, 3))
        self.assertTrue((root / "index.md").is_file())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_index.py' -v`
Expected: ERROR `No module named 'sb_core.index'`

- [ ] **Step 3: Implementa**

Aggiungi in fondo a `toolkit/sb_core/links.py`:

```python
def graph(wiki):
    """Grafo dei link risolti in modo univoco: (uscenti, entranti) per path di pagina."""
    pages = [p for p in wiki.pages() if p.meta is not None]
    outgoing = {p.path: set() for p in pages}
    incoming = {p.path: set() for p in pages}
    for page in pages:
        for link in page_links(page):
            if not link.target:
                continue
            _, targets = wiki.lookup(link.target)
            if len(targets) != 1:
                continue
            target = targets[0].path
            if target != page.path and target in incoming:
                outgoing[page.path].add(target)
                incoming[target].add(page.path)
    return outgoing, incoming
```

`toolkit/sb_core/index.py`:

```python
"""Indice generato (index.md) e mappa dei backlink (.sb/backlinks.json)."""
import json

from .links import graph
from .names import norm
from .wiki import LAYER_ORDER

INDEX_HEADER = "# Indice\n\n> Generato da `sb index`: non modificare a mano."


def _indexed_pages(wiki):
    return [p for p in wiki.pages() if p.meta is not None and p.type in wiki.types]


def build_index(wiki):
    pages = _indexed_pages(wiki)
    sections = [INDEX_HEADER]
    for layer in LAYER_ORDER:
        blocks = []
        layer_types = sorted((t for t in wiki.types.values() if t.layer == layer), key=lambda t: t.name)
        for typedef in layer_types:
            members = sorted((p for p in pages if p.type == typedef.name), key=lambda p: norm(p.stem))
            if not members:
                continue
            lines = [f"### {typedef.name} ({len(members)})"]
            for page in members:
                date = page.meta.get("updated") or page.meta.get("created")
                suffix = f" · {date}" if date else ""
                lines.append(f"- [[{page.stem}]]{suffix}")
            blocks.append("\n".join(lines))
        if blocks:
            sections.append(f"## {layer}\n\n" + "\n\n".join(blocks))
    return "\n\n".join(sections) + "\n"


def build_backlinks(wiki):
    _, incoming = graph(wiki)
    return {target: sorted(sources) for target, sources in sorted(incoming.items()) if sources}


def write_index(wiki):
    (wiki.root / "index.md").write_text(build_index(wiki), encoding="utf-8")
    sb_dir = wiki.root / ".sb"
    sb_dir.mkdir(exist_ok=True)
    backlinks = build_backlinks(wiki)
    (sb_dir / "backlinks.json").write_text(
        json.dumps(backlinks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"pages": len(_indexed_pages(wiki)), "index": "index.md", "backlinks": ".sb/backlinks.json"}
```

In `toolkit/sb_core/cli.py` aggiungi `from .index import write_index` e, prima di `COMMANDS`:

```python
def _add_index(sub, common):
    p = sub.add_parser("index", parents=[common], help="rigenera index.md e .sb/backlinks.json")
    p.set_defaults(handler=cmd_index)


def cmd_index(args):
    return write_index(_wiki(args)), 0
```

Aggiorna: `COMMANDS = [_add_version, _add_validate, _add_index]`

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core tests/test_index.py
git commit -m "feat(toolkit): generated index and backlinks"
```

---

### Task 6: `resolve`

**Files:**
- Create: `toolkit/sb_core/resolve.py`
- Modify: `toolkit/sb_core/cli.py` (comando `resolve`)
- Test: `tests/test_resolve.py`

**Interfaces:**
- Consumes: `Wiki.pages()`, `Page.title/.stem/.aliases/.type`, `names.norm`, `names.fold`, `links.link_target_name`
- Produces: `resolve.resolve(wiki, name, type_name=None, limit=5) -> {"query": str, "candidates": [{"path","title","type","score","match"}]}` con match ∈ `title` (1.0), `alias` (0.9), `partial` (0.75: tutte le parole della query sono nel titolo o in un alias), `fuzzy` (ratio × 0.7, incluso se ≥ 0.5). Ordinamento: punteggio decrescente, poi titolo. CLI: `sb resolve <nome> [--type T] [--limit N]`; un nome vuoto dà exit 2; `"[[Luca]]"` viene ripulito in `Luca`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_resolve.py`:

```python
import unittest

from helpers import WikiCase, md, run_cli
from sb_core.resolve import resolve
from sb_core.wiki import Wiki

FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi\naliases: [LB]"),
    "knowledge/people/Luca Verdi.md": md("type: person\ntitle: Luca Verdi"),
    "knowledge/people/Nicolò Rossi.md": md("type: person\ntitle: Nicolò Rossi"),
    "knowledge/projects/Migrazione DB.md": md("type: project\ntitle: Migrazione DB"),
}


class ResolveTest(WikiCase):
    def setUp(self):
        self.wiki = Wiki(self.make_wiki(FILES))

    def first(self, name, **kwargs):
        return resolve(self.wiki, name, **kwargs)["candidates"][0]

    def test_exact_title(self):
        top = self.first("luca  BIANCHI")
        self.assertEqual((top["title"], top["score"], top["match"]), ("Luca Bianchi", 1.0, "title"))
        self.assertEqual(top["path"], "knowledge/people/Luca Bianchi.md")
        self.assertEqual(top["type"], "person")

    def test_alias(self):
        top = self.first("lb")
        self.assertEqual((top["title"], top["match"], top["score"]), ("Luca Bianchi", "alias", 0.9))

    def test_partial_is_ambiguous(self):
        result = resolve(self.wiki, "Luca")["candidates"]
        self.assertEqual([(c["title"], c["match"]) for c in result],
                         [("Luca Bianchi", "partial"), ("Luca Verdi", "partial")])

    def test_accents_are_ignored(self):
        self.assertEqual(self.first("Nicolo")["title"], "Nicolò Rossi")

    def test_fuzzy(self):
        top = self.first("Luka Bianki")
        self.assertEqual((top["title"], top["match"]), ("Luca Bianchi", "fuzzy"))
        self.assertGreaterEqual(top["score"], 0.5)

    def test_type_filter_and_limit(self):
        self.assertEqual(resolve(self.wiki, "Migrazione DB", type_name="person")["candidates"], [])
        self.assertEqual(len(resolve(self.wiki, "Luca", limit=1)["candidates"]), 1)

    def test_cli(self):
        root = self.make_wiki(FILES)
        code, data, _ = run_cli("resolve", "[[Luca]]", "--wiki", root)
        self.assertEqual((code, data["query"], len(data["candidates"])), (0, "Luca", 2))
        code, _, _ = run_cli("resolve", "  ", "--wiki", root)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_resolve.py' -v`
Expected: ERROR `No module named 'sb_core.resolve'`

- [ ] **Step 3: Implementa**

`toolkit/sb_core/resolve.py`:

```python
"""Risoluzione di un nome libero verso le pagine della wiki, con punteggio."""
from difflib import SequenceMatcher

from .names import fold, norm

FUZZY_THRESHOLD = 0.5


def resolve(wiki, name, type_name=None, limit=5):
    query = norm(name)
    folded = fold(name)
    tokens = set(folded.split())
    candidates = []
    for page in wiki.pages():
        if page.meta is None or (type_name and page.type != type_name):
            continue
        score, match = _score(page, query, folded, tokens)
        if score >= FUZZY_THRESHOLD:
            candidates.append({
                "path": page.path, "title": page.title, "type": page.type,
                "score": score, "match": match,
            })
    candidates.sort(key=lambda c: (-c["score"], norm(c["title"])))
    return {"query": name, "candidates": candidates[:limit]}


def _score(page, query, folded, tokens):
    if norm(page.title) == query or norm(page.stem) == query:
        return 1.0, "title"
    if query in [norm(a) for a in page.aliases]:
        return 0.9, "alias"
    names = [page.title] + page.aliases
    if tokens and any(tokens <= set(fold(n).split()) for n in names):
        return 0.75, "partial"
    best = max(SequenceMatcher(None, folded, fold(n)).ratio() for n in names)
    return round(best * 0.7, 3), "fuzzy"
```

In `toolkit/sb_core/cli.py` aggiungi gli import `from .links import link_target_name` e `from .resolve import resolve`, poi prima di `COMMANDS`:

```python
def _add_resolve(sub, common):
    p = sub.add_parser("resolve", parents=[common], help="pagine candidate per un nome")
    p.add_argument("name")
    p.add_argument("--type", dest="type_name", help="limita a un tipo di pagina")
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(handler=cmd_resolve)


def cmd_resolve(args):
    name = link_target_name(args.name)
    if not name:
        raise UsageError("il nome da risolvere è vuoto")
    return resolve(_wiki(args), name, args.type_name, args.limit), 0
```

Aggiorna: `COMMANDS = [_add_version, _add_validate, _add_index, _add_resolve]`

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core tests/test_resolve.py
git commit -m "feat(toolkit): resolve names to pages with scoring"
```

---

### Task 7: `tasks list` (contratto JSON per gli artefatti)

**Files:**
- Create: `toolkit/sb_core/tasks.py`
- Modify: `toolkit/sb_core/cli.py` (comando `tasks list`)
- Test: `tests/test_tasks.py`

**Interfaces:**
- Consumes: `Wiki.pages()`, `Wiki.types["task"]`, `Wiki.thresholds["due_soon_days"]`, `wiki.closed_statuses`, `wiki.parse_date`, `links.link_target_name`, `names.norm`
- Produces:
  - `tasks.VIEWS = ("mine", "delegated", "overdue", "today", "week", "blocked", "all")`;
  - `tasks.task_record(page, today, closed) -> dict`, con le chiavi esatte `path, title, status, owner, delegated, due, overdue, priority, related, created`;
  - `tasks.list_tasks(wiki, view="mine", project=None, person=None, priority=None, today=None) -> list[dict]`.

  Semantica delle viste (gli item chiusi sono esclusi tranne in `blocked` e `all`):
  - `mine`: owner nullo;
  - `delegated`: owner valorizzato;
  - `overdue`: `due < oggi`;
  - `today`: `due ≤ oggi`;
  - `week`: `due ≤ oggi + due_soon_days`;
  - `blocked`: `status == blocked`;
  - `all`: tutto.

  Ordinamento: prima i task con scadenza, per data; poi per priorità high/medium/low/nessuna; poi per titolo.
  CLI: `sb tasks list [--view V] [--project P] [--person P] [--priority low|medium|high] [--json]` → `{"generated", "view", "tasks"}`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_tasks.py`:

```python
import datetime
import unittest

from helpers import WikiCase, md, run_cli
from sb_core.tasks import list_tasks
from sb_core.wiki import Wiki

TODAY = datetime.date(2026, 10, 2)

FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi"),
    "knowledge/projects/Migrazione DB.md": md("type: project\ntitle: Migrazione DB"),
    "operations/tasks/Mio scaduto.md": md(
        'type: task\ntitle: Mio scaduto\ndue: 2026-09-30\npriority: high\nrelated: ["[[Migrazione DB]]"]\ncreated: 2026-09-20'
    ),
    "operations/tasks/Mio oggi.md": md("type: task\ntitle: Mio oggi\nstatus: doing\ndue: 2026-10-02"),
    "operations/tasks/Mio senza data.md": md("type: task\ntitle: Mio senza data"),
    "operations/tasks/Delegato.md": md('type: task\ntitle: Delegato\nowner: "[[Luca Bianchi]]"\ndue: 2026-10-08\nstatus: blocked'),
    "operations/tasks/Chiuso.md": md("type: task\ntitle: Chiuso\nstatus: done\ndue: 2026-09-01"),
    "operations/tasks/Data sbagliata.md": md("type: task\ntitle: Data sbagliata\ndue: venerdì"),
}


class TasksTest(WikiCase):
    def setUp(self):
        self.root = self.make_wiki(FILES)
        self.wiki = Wiki(self.root)

    def titles(self, view, **kwargs):
        return [t["title"] for t in list_tasks(self.wiki, view=view, today=TODAY, **kwargs)]

    def test_views(self):
        self.assertEqual(self.titles("mine"), ["Mio scaduto", "Mio oggi", "Data sbagliata", "Mio senza data"])
        self.assertEqual(self.titles("delegated"), ["Delegato"])
        self.assertEqual(self.titles("overdue"), ["Mio scaduto"])
        self.assertEqual(self.titles("today"), ["Mio scaduto", "Mio oggi"])
        self.assertEqual(self.titles("week"), ["Mio scaduto", "Mio oggi", "Delegato"])
        self.assertEqual(self.titles("blocked"), ["Delegato"])
        self.assertEqual(len(self.titles("all")), 6)

    def test_filters(self):
        self.assertEqual(self.titles("all", project="Migrazione DB"), ["Mio scaduto"])
        self.assertEqual(self.titles("all", person="luca bianchi"), ["Delegato"])
        self.assertEqual(self.titles("all", priority="high"), ["Mio scaduto"])

    def test_record_contract(self):
        record = next(t for t in list_tasks(self.wiki, view="all", today=TODAY) if t["title"] == "Delegato")
        self.assertEqual(record, {
            "path": "operations/tasks/Delegato.md", "title": "Delegato", "status": "blocked",
            "owner": "Luca Bianchi", "delegated": True, "due": "2026-10-08", "overdue": False,
            "priority": None, "related": [], "created": None,
        })
        mine = next(t for t in list_tasks(self.wiki, view="all", today=TODAY) if t["title"] == "Mio scaduto")
        self.assertEqual((mine["status"], mine["overdue"], mine["related"], mine["created"]),
                         ("todo", True, ["Migrazione DB"], "2026-09-20"))

    def test_invalid_due_date_does_not_break(self):
        record = next(t for t in list_tasks(self.wiki, view="all", today=TODAY) if t["title"] == "Data sbagliata")
        self.assertEqual((record["due"], record["overdue"]), (None, False))

    def test_cli(self):
        code, data, _ = run_cli("tasks", "list", "--view", "overdue", "--today", "2026-10-02", "--json", "--wiki", self.root)
        self.assertEqual(code, 0)
        self.assertEqual([t["title"] for t in data["tasks"]], ["Mio scaduto"])
        self.assertEqual(data["view"], "overdue")
        self.assertIn("generated", data)
        code, _, _ = run_cli("tasks", "list", "--project", "[[Migrazione DB]]", "--view", "all", "--wiki", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(run_cli("tasks", "list", "--view", "boh", "--wiki", self.root)[0], 2)
        self.assertEqual(run_cli("tasks", "list", "--today", "ieri", "--wiki", self.root)[0], 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_tasks.py' -v`
Expected: ERROR `No module named 'sb_core.tasks'`

- [ ] **Step 3: Implementa**

`toolkit/sb_core/tasks.py`:

```python
"""Query sui task: viste, filtri e record JSON (contratto per gli artefatti)."""
import datetime

from .errors import UsageError
from .links import link_target_name
from .names import norm
from .wiki import closed_statuses, parse_date

VIEWS = ("mine", "delegated", "overdue", "today", "week", "blocked", "all")
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _iso(value):
    date = parse_date(value)
    return date.isoformat() if date else None


def task_record(page, today, closed):
    meta = page.meta
    status = meta.get("status") if isinstance(meta.get("status"), str) else "todo"
    owner = link_target_name(meta.get("owner"))
    due = parse_date(meta.get("due"))
    related = meta.get("related") if isinstance(meta.get("related"), list) else []
    priority = meta.get("priority")
    return {
        "path": page.path,
        "title": page.title,
        "status": status,
        "owner": owner,
        "delegated": owner is not None,
        "due": due.isoformat() if due else None,
        "overdue": bool(due and status not in closed and due < today),
        "priority": priority if isinstance(priority, str) else None,
        "related": [name for name in (link_target_name(r) for r in related) if name],
        "created": _iso(meta.get("created")),
    }


def list_tasks(wiki, view="mine", project=None, person=None, priority=None, today=None):
    if view not in VIEWS:
        raise UsageError(f"vista sconosciuta: {view} ({', '.join(VIEWS)})")
    today = today or datetime.date.today()
    closed = closed_statuses(wiki.types["task"])
    horizon = today + datetime.timedelta(days=wiki.thresholds["due_soon_days"])
    records = []
    for page in wiki.pages():
        if page.meta is None or page.type != "task":
            continue
        record = task_record(page, today, closed)
        if _in_view(record, view, today, horizon, closed) and _matches(record, project, person, priority):
            records.append(record)
    records.sort(key=_sort_key)
    return records


def _in_view(record, view, today, horizon, closed):
    if view == "all":
        return True
    if view == "blocked":
        return record["status"] == "blocked"
    if record["status"] in closed:
        return False
    due = parse_date(record["due"])
    if view == "mine":
        return not record["delegated"]
    if view == "delegated":
        return record["delegated"]
    if view == "overdue":
        return record["overdue"]
    if view == "today":
        return due is not None and due <= today
    return due is not None and due <= horizon  # week


def _matches(record, project, person, priority):
    related = {norm(r) for r in record["related"]}
    if priority and record["priority"] != priority:
        return False
    if project and norm(project) not in related:
        return False
    if person:
        people = set(related)
        if record["owner"]:
            people.add(norm(record["owner"]))
        if norm(person) not in people:
            return False
    return True


def _sort_key(record):
    return (
        record["due"] is None,
        record["due"] or "",
        PRIORITY_RANK.get(record["priority"], 3),
        norm(record["title"]),
    )
```

In `toolkit/sb_core/cli.py` aggiungi `from .tasks import VIEWS, list_tasks` e, prima di `COMMANDS`:

```python
def _add_tasks(sub, common):
    p = sub.add_parser("tasks", help="query sui task")
    tsub = p.add_subparsers(dest="tasks_command", metavar="<azione>")
    tsub.required = True
    lp = tsub.add_parser("list", parents=[common], help="task di una vista")
    lp.add_argument("--view", choices=VIEWS, default="mine")
    lp.add_argument("--project", help="titolo del progetto in 'related'")
    lp.add_argument("--person", help="persona come owner o in 'related'")
    lp.add_argument("--priority", choices=("low", "medium", "high"))
    lp.add_argument("--json", action="store_true", help="output JSON (sempre attivo)")
    lp.set_defaults(handler=cmd_tasks_list)


def cmd_tasks_list(args):
    records = list_tasks(
        _wiki(args), view=args.view,
        project=link_target_name(args.project), person=link_target_name(args.person),
        priority=args.priority, today=_today(args),
    )
    generated = datetime.datetime.now().isoformat(timespec="seconds")
    return {"generated": generated, "view": args.view, "tasks": records}, 0
```

Aggiorna: `COMMANDS = [_add_version, _add_validate, _add_index, _add_resolve, _add_tasks]`

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core tests/test_tasks.py
git commit -m "feat(toolkit): task views and JSON contract"
```

---

### Task 8: `sources stale` e `log`

**Files:**
- Create: `toolkit/sb_core/sources.py`, `toolkit/sb_core/log.py`
- Modify: `toolkit/sb_core/cli.py` (comandi `sources stale`, `log`)
- Test: `tests/test_sources.py`, `tests/test_log.py`

**Interfaces:**
- Consumes: `Wiki.pages()`, `Wiki.sources`, `wiki.parse_date`, `wiki.DEFAULT_SOURCE_STALE_DAYS`, `errors.UsageError`
- Produces:
  - `sources.parse_external(ref) -> (system, scope | None)`, dove scope è il prefisso alfanumerico dopo `:`;
  - `sources.registry_entry(wiki, system, scope) -> (source_id | None, entry | None)`, che preferisce l'entry con lo stesso scope e altrimenti un'entry senza scope dello stesso sistema;
  - `sources.ONE_OFF_SYSTEMS = ("url", "mail")`;
  - `sources.stale_sources(wiki, today) -> list[{"path","title","external","source_id","synced","age_days","threshold_days","reason"}]`, con reason ∈ `never-synced` o `expired`, ordinate con prima le mai sincronizzate e poi per età decrescente. Esclude `authority: migrated` e i sistemi one-off.
  - `log.LOG_HEADER`; `log.append_log(root, message, op="note", now=None) -> {"logged": str}`, che scrive la riga `- AAAA-MM-GG HH:MM · <op> · <messaggio>` comprimendo gli a-capo.
  - CLI: `sb sources stale` → `{"stale": [...]}`; `sb log <messaggio> [--op OP]`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_sources.py`:

```python
import datetime
import unittest

from helpers import WikiCase, md, run_cli
from sb_core.sources import parse_external, stale_sources
from sb_core.wiki import Wiki

TODAY = datetime.date(2026, 10, 2)


def note(title, external, extra=""):
    return md(f'type: source-note\ntitle: {title}\nexternal: "{external}"\n{extra}')


FILES = {
    "knowledge/sources/Fresca.md": note("Fresca", "confluence:ENG/1", "synced: 2026-09-20"),
    "knowledge/sources/Vecchia.md": note("Vecchia", "confluence:ENG/2", "synced: 2026-08-01"),
    "knowledge/sources/Jira.md": note("Jira", "jira:PLAT-1", "synced: 2026-09-15"),
    "knowledge/sources/Mai.md": note("Mai", "confluence:ENG/3"),
    "knowledge/sources/Migrata.md": note("Migrata", "confluence:OLD/4", "synced: 2025-01-01\nauthority: migrated"),
    "knowledge/sources/Articolo.md": note("Articolo", "url:https://example.com/a", "synced: 2025-01-01"),
    "knowledge/sources/Altro spazio.md": note("Altro spazio", "confluence:HR/9", "synced: 2026-08-25"),
}


class SourcesTest(WikiCase):
    def test_parse_external(self):
        self.assertEqual(parse_external("confluence:ENG/123"), ("confluence", "ENG"))
        self.assertEqual(parse_external("jira:PLAT-123"), ("jira", "PLAT"))
        self.assertEqual(parse_external("mail:"), ("mail", None))

    def test_stale_sources(self):
        items = stale_sources(Wiki(self.make_wiki(FILES)), TODAY)
        self.assertEqual([i["title"] for i in items], ["Mai", "Vecchia", "Altro spazio", "Jira"])
        by_title = {i["title"]: i for i in items}
        self.assertEqual(by_title["Mai"]["reason"], "never-synced")
        self.assertIsNone(by_title["Mai"]["age_days"])
        self.assertEqual((by_title["Vecchia"]["age_days"], by_title["Vecchia"]["source_id"]), (62, "conf-eng"))
        self.assertEqual((by_title["Jira"]["source_id"], by_title["Jira"]["threshold_days"]), ("jira-plat", 14))
        self.assertEqual((by_title["Altro spazio"]["source_id"], by_title["Altro spazio"]["threshold_days"]), (None, 30))
        self.assertEqual(by_title["Vecchia"]["external"], "confluence:ENG/2")
        self.assertEqual(by_title["Vecchia"]["synced"], "2026-08-01")

    def test_cli(self):
        code, data, _ = run_cli("sources", "stale", "--today", "2026-10-02", "--wiki", self.make_wiki(FILES))
        self.assertEqual((code, len(data["stale"])), (0, 4))


if __name__ == "__main__":
    unittest.main()
```

`tests/test_log.py`:

```python
import datetime
import re
import unittest

from helpers import WikiCase, run_cli
from sb_core.log import LOG_HEADER, append_log

LINE = re.compile(r"^- \d{4}-\d{2}-\d{2} \d{2}:\d{2} · (\w+) · (.+)$")


class LogTest(WikiCase):
    def test_append_creates_and_appends(self):
        root = self.make_wiki()
        now = datetime.datetime(2026, 10, 2, 9, 30)
        result = append_log(root, "1:1 Luca\nBianchi:   2 task", op="put", now=now)
        self.assertEqual(result["logged"], "- 2026-10-02 09:30 · put · 1:1 Luca Bianchi: 2 task")
        append_log(root, "riallineate 3 sorgenti", op="sync", now=now)
        text = (root / "log.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith(LOG_HEADER))
        lines = [l for l in text.splitlines() if l.startswith("- ")]
        self.assertEqual([LINE.match(l).group(1) for l in lines], ["put", "sync"])

    def test_appends_after_file_without_trailing_newline(self):
        root = self.make_wiki({"log.md": "# Log\n\n- vecchia riga"})
        append_log(root, "nuova", now=datetime.datetime(2026, 10, 2, 9, 30))
        self.assertEqual((root / "log.md").read_text(encoding="utf-8").splitlines()[-2:],
                         ["- vecchia riga", "- 2026-10-02 09:30 · note · nuova"])

    def test_cli(self):
        root = self.make_wiki()
        code, data, _ = run_cli("log", "Ciao", "--op", "sync", "--wiki", root)
        self.assertEqual(code, 0)
        self.assertTrue(LINE.match(data["logged"]))
        self.assertEqual(run_cli("log", "   ", "--wiki", root)[0], 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_sources.py' -v && python3 -m unittest discover -s tests -p 'test_log.py' -v`
Expected: ERROR `No module named 'sb_core.sources'`

- [ ] **Step 3: Implementa**

`toolkit/sb_core/sources.py`:

```python
"""Source-note da riallineare con le sorgenti esterne registrate."""
import re

from .wiki import DEFAULT_SOURCE_STALE_DAYS, parse_date

ONE_OFF_SYSTEMS = ("url", "mail")
_SCOPE = re.compile(r"[A-Za-z0-9_]+")


def parse_external(ref):
    system, _, rest = ref.partition(":")
    match = _SCOPE.match(rest)
    return system, (match.group(0) if match else None)


def registry_entry(wiki, system, scope):
    fallback = (None, None)
    for source_id, entry in sorted(wiki.sources.items()):
        if entry.get("system") != system:
            continue
        entry_scope = entry.get("scope")
        if entry_scope is not None and scope is not None and str(entry_scope) == scope:
            return source_id, entry
        if entry_scope is None and fallback == (None, None):
            fallback = (source_id, entry)
    return fallback


def stale_sources(wiki, today):
    results = []
    for page in wiki.pages():
        if page.meta is None or page.type != "source-note":
            continue
        meta = page.meta
        if meta.get("authority") == "migrated":
            continue
        external = meta.get("external") if isinstance(meta.get("external"), str) else None
        system, scope = parse_external(external) if external else (None, None)
        if system in ONE_OFF_SYSTEMS:
            continue
        source_id, entry = registry_entry(wiki, system, scope) if system else (None, None)
        threshold = (entry or {}).get("stale_after_days")
        if not isinstance(threshold, int) or isinstance(threshold, bool):
            threshold = DEFAULT_SOURCE_STALE_DAYS
        synced = parse_date(meta.get("synced"))
        if synced is None:
            reason, age = "never-synced", None
        else:
            age = (today - synced).days
            if age <= threshold:
                continue
            reason = "expired"
        results.append({
            "path": page.path, "title": page.title, "external": external, "source_id": source_id,
            "synced": synced.isoformat() if synced else None, "age_days": age,
            "threshold_days": threshold, "reason": reason,
        })
    results.sort(key=lambda r: (r["age_days"] is not None, -(r["age_days"] or 0), r["path"]))
    return results
```

`toolkit/sb_core/log.py`:

```python
"""Registro cronologico delle operazioni (log.md, solo in aggiunta)."""
import datetime
from pathlib import Path

from .errors import UsageError

LOG_HEADER = "# Log\n\nRegistro cronologico delle operazioni sulla wiki (solo in aggiunta).\n\n"


def append_log(root, message, op="note", now=None):
    message = " ".join(str(message).split())
    op = " ".join(str(op).split()) or "note"
    if not message:
        raise UsageError("il messaggio di log è vuoto")
    now = now or datetime.datetime.now()
    line = f"- {now:%Y-%m-%d %H:%M} · {op} · {message}"
    path = Path(root) / "log.md"
    if not path.exists():
        path.write_text(LOG_HEADER, encoding="utf-8")
    existing = path.read_text(encoding="utf-8")
    prefix = "" if existing.endswith("\n") or not existing else "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(prefix + line + "\n")
    return {"logged": line}
```

In `toolkit/sb_core/cli.py` aggiungi `from .log import append_log` e `from .sources import stale_sources`, poi prima di `COMMANDS`:

```python
def _add_sources(sub, common):
    p = sub.add_parser("sources", help="sorgenti esterne")
    ssub = p.add_subparsers(dest="sources_command", metavar="<azione>")
    ssub.required = True
    sp = ssub.add_parser("stale", parents=[common], help="source-note da riallineare")
    sp.set_defaults(handler=cmd_sources_stale)


def cmd_sources_stale(args):
    return {"stale": stale_sources(_wiki(args), _today(args))}, 0


def _add_log(sub, common):
    p = sub.add_parser("log", parents=[common], help="aggiunge una riga a log.md")
    p.add_argument("message")
    p.add_argument("--op", default="note", help="nome dell'operazione (put, sync, …)")
    p.set_defaults(handler=cmd_log)


def cmd_log(args):
    wiki = _wiki(args)
    return append_log(wiki.root, args.message, args.op), 0
```

Aggiorna: `COMMANDS = [_add_version, _add_validate, _add_index, _add_resolve, _add_tasks, _add_sources, _add_log]`

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core tests/test_sources.py tests/test_log.py
git commit -m "feat(toolkit): stale source detection and operation log"
```

---

### Task 9: `lint` e `status`

**Files:**
- Create: `toolkit/sb_core/lint.py`, `toolkit/sb_core/status.py`
- Modify: `toolkit/sb_core/cli.py` (comandi `lint`, `status`)
- Test: `tests/test_lint.py`, `tests/test_status.py`

**Interfaces:**
- Consumes: `validate.validate`, `validate.Issue`, `links.graph`, `links.link_target_name`, `sources.stale_sources`, `tasks.list_tasks`, `wiki.is_open`, `wiki.parse_date`, `names.norm`
- Produces:
  - `lint.lint(wiki, today) -> list[Issue]`: tutte le issue di `validate` più `orphan` (pagina knowledge/operations senza link in entrata né in uscita), `stale-source`, `overdue-task`, `stale-item` (item operations con campo `status` nello schema, aperto, con `updated` o `created` più vecchio di `stale_operations_days`). Tutte le nuove sono warning.
  - `status.status(wiki, today) -> {"today", "tasks": {"overdue", "due_soon", "delegated_overdue"}, "one_on_one_gaps", "stale_sources", "open_proposals", "lint": {"errors", "warnings"}}`;
  - `status.one_on_one_gaps(wiki, today) -> list[{"person","last","days"}]`;
  - `status.count_open_proposals(wiki) -> int`, che conta le righe `- [ ]` in `schema/proposals.md`.
  - CLI: `sb lint` → `{"ok", "summary": {codice: n}, "issues"}` (exit 1 se ci sono issue); `sb status`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_lint.py`:

```python
import datetime
import unittest
from collections import Counter

from helpers import WikiCase, md, run_cli
from sb_core.lint import lint
from sb_core.wiki import Wiki

TODAY = datetime.date(2026, 10, 2)

FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi"),
    "knowledge/topics/Orfano.md": md("type: topic\ntitle: Orfano"),
    "knowledge/topics/Con link rotto.md": md("type: topic\ntitle: Con link rotto", "[[Fantasma]]\n"),
    "operations/tasks/Scaduto.md": md(
        'type: task\ntitle: Scaduto\ndue: 2026-09-01\nowner: "[[Luca Bianchi]]"\ncreated: 2026-09-01'
    ),
    "operations/risks/Rischio fermo.md": md(
        "type: risk\ntitle: Rischio fermo\nstatus: open\nupdated: 2026-08-01", "Riguarda [[Luca Bianchi]].\n"
    ),
    "operations/risks/Rischio chiuso.md": md(
        "type: risk\ntitle: Rischio chiuso\nstatus: closed\nupdated: 2026-01-01", "[[Luca Bianchi]]\n"
    ),
    "knowledge/sources/Vecchia.md": md(
        'type: source-note\ntitle: Vecchia\nexternal: "confluence:ENG/2"\nsynced: 2026-08-01', "Su [[Luca Bianchi]].\n"
    ),
}


class LintTest(WikiCase):
    def test_lint_codes(self):
        issues = lint(Wiki(self.make_wiki(FILES)), TODAY)
        self.assertEqual(Counter((i.path, i.code) for i in issues), Counter({
            ("knowledge/topics/Orfano.md", "orphan"): 1,
            ("knowledge/topics/Con link rotto.md", "broken-link"): 1,
            ("knowledge/topics/Con link rotto.md", "orphan"): 1,
            ("operations/tasks/Scaduto.md", "overdue-task"): 1,
            ("operations/tasks/Scaduto.md", "stale-item"): 1,
            ("operations/risks/Rischio fermo.md", "stale-item"): 1,
            ("knowledge/sources/Vecchia.md", "stale-source"): 1,
        }))
        severities = {i.code: i.severity for i in issues}
        self.assertEqual(severities["broken-link"], "error")
        self.assertEqual(severities["orphan"], "warning")

    def test_cli(self):
        code, data, _ = run_cli("lint", "--today", "2026-10-02", "--wiki", self.make_wiki(FILES))
        self.assertEqual((code, data["ok"], data["summary"]["orphan"]), (1, False, 2))
        code, data, _ = run_cli("lint", "--today", "2026-10-02", "--wiki", self.make_wiki())
        self.assertEqual((code, data["ok"], data["summary"]), (0, True, {}))


if __name__ == "__main__":
    unittest.main()
```

`tests/test_status.py`:

```python
import datetime
import unittest

from helpers import WikiCase, md, run_cli
from sb_core.status import status
from sb_core.wiki import Wiki

TODAY = datetime.date(2026, 10, 2)


def one_on_one(day, person):
    return md(f'type: one-on-one\ntitle: {day} 1on1 {person}\nwith: "[[{person}]]"\ndate: {day}')


FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi"),
    "knowledge/people/Anna Neri.md": md("type: person\ntitle: Anna Neri"),
    "operations/tasks/Mio scaduto.md": md("type: task\ntitle: Mio scaduto\ndue: 2026-09-30"),
    "operations/tasks/In scadenza.md": md("type: task\ntitle: In scadenza\ndue: 2026-10-05"),
    "operations/tasks/Delegato in ritardo.md": md(
        'type: task\ntitle: Delegato in ritardo\nowner: "[[Luca Bianchi]]"\ndue: 2026-09-28'
    ),
    "operations/tasks/Delegato futuro.md": md('type: task\ntitle: Delegato futuro\nowner: "[[Anna Neri]]"\ndue: 2026-10-20'),
    "operations/one-on-ones/2026-08-01 1on1 Luca Bianchi.md": one_on_one("2026-08-01", "Luca Bianchi"),
    "operations/one-on-ones/2026-09-01 1on1 Luca Bianchi.md": one_on_one("2026-09-01", "Luca Bianchi"),
    "operations/one-on-ones/2026-09-25 1on1 Anna Neri.md": one_on_one("2026-09-25", "Anna Neri"),
    "schema/proposals.md": "# Proposte\n\n- [ ] P1 · vendor\n  - segnale: x\n- [x] P2 · fatto\n- [-] P3 · scartata\n- [ ] P4 · altro\n",
}


class StatusTest(WikiCase):
    def test_status(self):
        data = status(Wiki(self.make_wiki(FILES)), TODAY)
        titles = {k: [t["title"] for t in v] for k, v in data["tasks"].items()}
        self.assertEqual(titles, {
            "overdue": ["Mio scaduto"], "due_soon": ["In scadenza"], "delegated_overdue": ["Delegato in ritardo"],
        })
        self.assertEqual(data["one_on_one_gaps"], [{"person": "Luca Bianchi", "last": "2026-09-01", "days": 31}])
        self.assertEqual(data["open_proposals"], 2)
        self.assertEqual(data["stale_sources"], [])
        self.assertEqual(set(data["lint"]), {"errors", "warnings"})
        self.assertEqual(data["today"], "2026-10-02")

    def test_cli(self):
        code, data, _ = run_cli("status", "--today", "2026-10-02", "--wiki", self.make_wiki(FILES))
        self.assertEqual((code, data["open_proposals"]), (0, 2))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_lint.py' -v`
Expected: ERROR `No module named 'sb_core.lint'`

- [ ] **Step 3: Implementa**

`toolkit/sb_core/lint.py`:

```python
"""Lint strutturale: validazione + orfani, sorgenti stantie, task scaduti, item fermi."""
from .links import graph
from .sources import stale_sources
from .tasks import list_tasks
from .validate import Issue, validate
from .wiki import is_open, parse_date


def lint(wiki, today):
    issues = list(validate(wiki))
    issues.extend(_orphans(wiki))
    for item in stale_sources(wiki, today):
        detail = "mai sincronizzata" if item["age_days"] is None else f"sincronizzata {item['age_days']} giorni fa"
        issues.append(Issue(item["path"], "stale-source", f"sorgente da riallineare ({detail})", "warning"))
    for task in list_tasks(wiki, view="overdue", today=today):
        issues.append(Issue(task["path"], "overdue-task", f"task scaduto il {task['due']}", "warning"))
    issues.extend(_stale_items(wiki, today))
    return issues


def _orphans(wiki):
    outgoing, incoming = graph(wiki)
    return [
        Issue(path, "orphan", "nessun link in entrata né in uscita", "warning")
        for path in sorted(outgoing)
        if not outgoing[path] and not incoming[path] and not path.startswith("outputs/")
    ]


def _stale_items(wiki, today):
    limit = wiki.thresholds["stale_operations_days"]
    issues = []
    for page in wiki.pages():
        if page.meta is None:
            continue
        typedef = wiki.types.get(page.type)
        if typedef is None or typedef.layer != "operations" or "status" not in typedef.fields:
            continue
        if not is_open(page, typedef):
            continue
        last = parse_date(page.meta.get("updated")) or parse_date(page.meta.get("created"))
        if last is None:
            continue
        age = (today - last).days
        if age > limit:
            issues.append(Issue(page.path, "stale-item", f"aperto e senza aggiornamenti da {age} giorni", "warning"))
    return issues
```

`toolkit/sb_core/status.py`:

```python
"""Dati del cruscotto /sb:status."""
import re

from .lint import lint
from .links import link_target_name
from .names import norm
from .sources import stale_sources
from .tasks import list_tasks
from .wiki import parse_date

_OPEN_PROPOSAL = re.compile(r"^\s*- \[ \] ", re.MULTILINE)


def status(wiki, today):
    overdue = list_tasks(wiki, view="overdue", today=today)
    week = list_tasks(wiki, view="week", today=today)
    issues = lint(wiki, today)
    return {
        "today": today.isoformat(),
        "tasks": {
            "overdue": [t for t in overdue if not t["delegated"]],
            "due_soon": [t for t in week if not t["overdue"]],
            "delegated_overdue": [t for t in overdue if t["delegated"]],
        },
        "one_on_one_gaps": one_on_one_gaps(wiki, today),
        "stale_sources": stale_sources(wiki, today),
        "open_proposals": count_open_proposals(wiki),
        "lint": {
            "errors": sum(1 for i in issues if i.severity == "error"),
            "warnings": sum(1 for i in issues if i.severity == "warning"),
        },
    }


def one_on_one_gaps(wiki, today):
    if "one-on-one" not in wiki.types:
        return []
    gap = wiki.thresholds["one_on_one_gap_days"]
    last = {}
    for page in wiki.pages():
        if page.meta is None or page.type != "one-on-one":
            continue
        person = link_target_name(page.meta.get("with"))
        when = parse_date(page.meta.get("date")) or parse_date(page.meta.get("created"))
        if not person or when is None:
            continue
        key = norm(person)
        if key not in last or when > last[key][1]:
            last[key] = (person, when)
    gaps = [
        {"person": person, "last": when.isoformat(), "days": (today - when).days}
        for person, when in last.values()
        if (today - when).days > gap
    ]
    gaps.sort(key=lambda g: (-g["days"], norm(g["person"])))
    return gaps


def count_open_proposals(wiki):
    path = wiki.root / "schema" / "proposals.md"
    if not path.is_file():
        return 0
    return len(_OPEN_PROPOSAL.findall(path.read_text(encoding="utf-8")))
```

Nota su `count_open_proposals`: la regex conta anche le sotto-voci indentate che iniziano con `- [ ]`. Le sotto-voci delle proposte sono `- segnale:` e `- proposta:`, quindi non collidono. Il test del passo 1 lo copre con una sotto-voce `- segnale: x`.

In `toolkit/sb_core/cli.py` aggiungi `from collections import Counter`, `from .lint import lint` e `from .status import status`, poi prima di `COMMANDS`:

```python
def _add_lint(sub, common):
    p = sub.add_parser("lint", parents=[common], help="controlli strutturali della wiki")
    p.set_defaults(handler=cmd_lint)


def cmd_lint(args):
    issues = lint(_wiki(args), _today(args))
    summary = dict(sorted(Counter(i.code for i in issues).items()))
    return {"ok": not issues, "summary": summary, "issues": [i.to_dict() for i in issues]}, 1 if issues else 0


def _add_status(sub, common):
    p = sub.add_parser("status", parents=[common], help="dati del cruscotto")
    p.set_defaults(handler=cmd_status)


def cmd_status(args):
    return status(_wiki(args), _today(args)), 0
```

Aggiorna: `COMMANDS = [_add_version, _add_validate, _add_index, _add_resolve, _add_tasks, _add_sources, _add_log, _add_lint, _add_status]`

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core tests/test_lint.py tests/test_status.py
git commit -m "feat(toolkit): structural lint and status dashboard data"
```

---

### Task 10: `migrate`

**Files:**
- Create: `toolkit/sb_core/migrate.py`
- Modify: `toolkit/sb_core/cli.py` (comando `migrate`)
- Test: `tests/test_migrate.py`

**Interfaces:**
- Consumes: `Wiki.pages()`, `Wiki.root`, `Wiki.invalidate()`, `frontmatter.render`, `links.WIKILINK`, `links.parse_link`, `names.norm`, `names.title_problem`, `errors.PlanError`
- Produces:
  - `migrate.load_plan(path) -> list[dict]`;
  - `migrate.migrate(wiki, ops, dry_run=False) -> {"dry_run": bool, "changes": [...], "written": [paths]}`. Il piano viene validato tutto prima di scrivere: un errore in qualsiasi operazione → `PlanError` e nessun file toccato.
  - Operazioni:
    - `{"op":"move","path","to","set"?}`;
    - `{"op":"retitle","path","title"}`: rinomina il file, imposta `title`, aggiunge il vecchio titolo agli `aliases` e riscrive i wikilink in tutta la wiki mantenendo `#sezione` e `|testo`;
    - `{"op":"rename_field","type","from","to"}`;
    - `{"op":"set","path","fields"}`: `null` rimuove il campo.

    Solo le pagine modificate vengono riscritte.
  - CLI: `sb migrate <piano.json> [--dry-run]`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_migrate.py`:

```python
import json
import unittest

from helpers import WikiCase, md, run_cli
from sb_core.errors import PlanError
from sb_core.frontmatter import parse
from sb_core.migrate import migrate
from sb_core.validate import validate
from sb_core.wiki import Wiki

TASK = "operations/tasks/Chiamare Acme.md"
FILES = {
    "knowledge/topics/Acme.md": md("type: topic\ntitle: Acme", "Fornitore storico.\n"),
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi\nrole: EM"),
    TASK: md(
        'type: task\ntitle: Chiamare Acme\nowner: "[[Luca Bianchi]]"\nrelated: ["[[Acme]]"]',
        "Parlare con [[Luca Bianchi|Luca]] di [[Acme#contratto]].\n",
    ),
}


class MigrateTest(WikiCase):
    def setUp(self):
        self.root = self.make_wiki(FILES)

    def meta(self, rel):
        return parse((self.root / rel).read_text(encoding="utf-8"))

    def test_move_and_retype(self):
        result = migrate(Wiki(self.root), [
            {"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/vendors/Acme.md", "set": {"type": "vendor"}},
        ])
        self.assertFalse((self.root / "knowledge/topics/Acme.md").exists())
        meta, body = self.meta("knowledge/vendors/Acme.md")
        self.assertEqual((meta["type"], body), ("vendor", "Fornitore storico.\n"))
        self.assertEqual(result["changes"], [{"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/vendors/Acme.md"}])
        self.assertEqual([i.code for i in validate(Wiki(self.root)) if i.severity == "error"], [])

    def test_pure_move_keeps_bytes(self):
        before = (self.root / "knowledge/topics/Acme.md").read_bytes()
        migrate(Wiki(self.root), [{"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/topics/sub/Acme.md"}])
        self.assertEqual((self.root / "knowledge/topics/sub/Acme.md").read_bytes(), before)

    def test_retitle_rewrites_links(self):
        result = migrate(Wiki(self.root), [
            {"op": "retitle", "path": "knowledge/people/Luca Bianchi.md", "title": "Luca Bianchi Rossi"},
        ])
        self.assertFalse((self.root / "knowledge/people/Luca Bianchi.md").exists())
        meta, _ = self.meta("knowledge/people/Luca Bianchi Rossi.md")
        self.assertEqual((meta["title"], meta["aliases"]), ("Luca Bianchi Rossi", ["Luca Bianchi"]))
        task_meta, task_body = self.meta(TASK)
        self.assertEqual(task_meta["owner"], "[[Luca Bianchi Rossi]]")
        self.assertEqual(task_body, "Parlare con [[Luca Bianchi Rossi|Luca]] di [[Acme#contratto]].\n")
        self.assertEqual(result["changes"][0]["links_rewritten"], 2)
        self.assertEqual(validate(Wiki(self.root)), [])

    def test_rename_field_touches_only_matching_pages(self):
        task_before = (self.root / TASK).read_text(encoding="utf-8")
        migrate(Wiki(self.root), [{"op": "rename_field", "type": "person", "from": "role", "to": "position"}])
        meta, _ = self.meta("knowledge/people/Luca Bianchi.md")
        self.assertEqual(list(meta), ["type", "title", "position"])
        self.assertEqual((self.root / TASK).read_text(encoding="utf-8"), task_before)

    def test_set_and_remove_fields(self):
        migrate(Wiki(self.root), [{"op": "set", "path": TASK, "fields": {"priority": "high", "owner": None}}])
        meta, _ = self.meta(TASK)
        self.assertEqual(meta["priority"], "high")
        self.assertNotIn("owner", meta)

    def test_dry_run_writes_nothing(self):
        result = migrate(Wiki(self.root), [{"op": "set", "path": TASK, "fields": {"priority": "high"}}], dry_run=True)
        self.assertEqual((result["dry_run"], result["written"], len(result["changes"])), (True, [], 1))
        self.assertNotIn("priority", self.meta(TASK)[0])

    def test_errors_leave_wiki_untouched(self):
        plans = [
            [{"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/vendors/Acme.md"},
             {"op": "move", "path": "knowledge/topics/Nessuno.md", "to": "knowledge/vendors/Nessuno.md"}],
            [{"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/people/Luca Bianchi.md"}],
            [{"op": "retitle", "path": TASK, "title": "Titolo: non valido"}],
            [{"op": "explode"}],
            [{"op": "move", "path": "knowledge/topics/Acme.md", "to": "../fuori.md"}],
        ]
        for ops in plans:
            with self.subTest(ops=ops):
                with self.assertRaises(PlanError):
                    migrate(Wiki(self.root), ops)
                self.assertTrue((self.root / "knowledge/topics/Acme.md").exists())

    def test_cli(self):
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"ops": [{"op": "set", "path": TASK, "fields": {"priority": "low"}}]}), encoding="utf-8")
        code, data, _ = run_cli("migrate", plan, "--dry-run", "--wiki", self.root)
        self.assertEqual((code, data["dry_run"]), (0, True))
        code, data, _ = run_cli("migrate", plan, "--wiki", self.root)
        self.assertEqual((code, data["written"]), (0, [TASK]))
        plan.write_text('{"ops": []}', encoding="utf-8")
        self.assertEqual(run_cli("migrate", plan, "--wiki", self.root)[0], 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_migrate.py' -v`
Expected: ERROR `No module named 'sb_core.migrate'`

- [ ] **Step 3: Implementa**

`toolkit/sb_core/migrate.py`:

```python
"""Migrazioni della wiki: spostamenti, cambi di titolo, rinomina e modifica di campi.

Il piano viene applicato prima in memoria; i file vengono toccati solo se tutte
le operazioni sono valide.
"""
import json
import os
from pathlib import Path

from .errors import PlanError
from .frontmatter import render
from .links import WIKILINK, parse_link
from .names import norm, title_problem


def load_plan(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PlanError(f"piano illeggibile: {exc}")
    ops = data.get("ops") if isinstance(data, dict) else None
    if not isinstance(ops, list) or not ops:
        raise PlanError("il piano deve contenere una lista 'ops' non vuota")
    return ops


class _Context(object):
    def __init__(self, wiki):
        self.wiki = wiki
        self.state = {p.path: [dict(p.meta), p.body] for p in wiki.pages() if p.meta is not None}
        self.touched = set()
        self.moves = []
        self.moved_from = set()

    def require(self, path, index):
        if path not in self.state:
            raise PlanError(f"operazione {index}: pagina '{path}' non trovata o con frontmatter illeggibile")

    def check_destination(self, src, dst, index):
        if not isinstance(dst, str) or not dst.endswith(".md") or dst.startswith("/") or ".." in dst.split("/"):
            raise PlanError(f"operazione {index}: la destinazione deve essere un percorso .md relativo alla wiki")
        if dst == src:
            return
        if dst in self.state:
            raise PlanError(f"operazione {index}: '{dst}' esiste già")
        dst_abs, src_abs = self.wiki.root / dst, self.wiki.root / src
        if dst_abs.exists() and dst not in self.moved_from:
            same_file = src_abs.exists() and os.path.samefile(str(src_abs), str(dst_abs))
            if not same_file:
                raise PlanError(f"operazione {index}: '{dst}' esiste già")

    def move(self, src, dst):
        if dst == src:
            return
        self.state[dst] = self.state.pop(src)
        self.moves.append((src, dst))
        self.moved_from.add(src)
        if src in self.touched:
            self.touched.discard(src)
            self.touched.add(dst)


def _apply_fields(meta, fields, index):
    if not isinstance(fields, dict):
        raise PlanError(f"operazione {index}: i campi devono essere una mappa")
    for key, value in fields.items():
        if value is None:
            meta.pop(key, None)
        else:
            meta[key] = value


def _op_move(ctx, op, index):
    src, dst = op.get("path"), op.get("to")
    ctx.require(src, index)
    ctx.check_destination(src, dst, index)
    ctx.move(src, dst)
    fields = op.get("set")
    if fields:
        _apply_fields(ctx.state[dst][0], fields, index)
        ctx.touched.add(dst)
    return [{"op": "move", "path": src, "to": dst}]


def _op_retitle(ctx, op, index):
    path, new_title = op.get("path"), op.get("title")
    ctx.require(path, index)
    problem = title_problem(new_title)
    if problem:
        raise PlanError(f"operazione {index}: titolo non valido: {problem}")
    folder, filename = path.rsplit("/", 1)
    old_title = filename[:-3]
    new_path = f"{folder}/{new_title}.md"
    ctx.check_destination(path, new_path, index)
    ctx.move(path, new_path)
    meta = ctx.state[new_path][0]
    meta["title"] = new_title
    if norm(old_title) != norm(new_title):
        aliases = [a for a in (meta.get("aliases") or []) if isinstance(a, str)]
        if old_title not in aliases:
            aliases.append(old_title)
        meta["aliases"] = aliases
    ctx.touched.add(new_path)
    count = _rewrite_links(ctx, old_title, new_title)
    return [{"op": "retitle", "path": path, "to": new_path, "links_rewritten": count}]


def _rewrite_links(ctx, old, new):
    key = norm(old)
    counter = [0]

    def replace(match):
        link = parse_link(match.group(1))
        if norm(link.target) != key:
            return match.group(0)
        counter[0] += 1
        text = new
        if link.heading:
            text += "#" + link.heading
        if link.display:
            text += "|" + link.display
        return "[[" + text + "]]"

    def rewrite(value):
        if isinstance(value, str):
            return WIKILINK.sub(replace, value)
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        if isinstance(value, dict):
            return {k: rewrite(v) for k, v in value.items()}
        return value

    for path, entry in ctx.state.items():
        new_meta, new_body = rewrite(entry[0]), rewrite(entry[1])
        if new_meta != entry[0] or new_body != entry[1]:
            entry[0], entry[1] = new_meta, new_body
            ctx.touched.add(path)
    return counter[0]


def _op_rename_field(ctx, op, index):
    type_name, old, new = op.get("type"), op.get("from"), op.get("to")
    if not all(isinstance(x, str) and x for x in (type_name, old, new)):
        raise PlanError(f"operazione {index}: 'type', 'from' e 'to' sono obbligatori")
    changes = []
    for path in sorted(ctx.state):
        meta = ctx.state[path][0]
        if meta.get("type") != type_name or old not in meta:
            continue
        if new in meta:
            raise PlanError(f"operazione {index}: {path} ha già il campo '{new}'")
        ctx.state[path][0] = {(new if k == old else k): v for k, v in meta.items()}
        ctx.touched.add(path)
        changes.append({"op": "rename_field", "path": path, "from": old, "to": new})
    return changes


def _op_set(ctx, op, index):
    path, fields = op.get("path"), op.get("fields")
    ctx.require(path, index)
    if not fields:
        raise PlanError(f"operazione {index}: 'fields' è obbligatorio")
    _apply_fields(ctx.state[path][0], fields, index)
    ctx.touched.add(path)
    return [{"op": "set", "path": path, "fields": sorted(fields)}]


OPS = {"move": _op_move, "retitle": _op_retitle, "rename_field": _op_rename_field, "set": _op_set}


def migrate(wiki, ops, dry_run=False):
    if not isinstance(ops, list) or not ops:
        raise PlanError("il piano deve contenere almeno un'operazione")
    ctx = _Context(wiki)
    changes = []
    for index, op in enumerate(ops, 1):
        kind = op.get("op") if isinstance(op, dict) else None
        if kind not in OPS:
            raise PlanError(f"operazione {index}: 'op' sconosciuta ({kind}); ammesse: {', '.join(OPS)}")
        changes.extend(OPS[kind](ctx, op, index))
    if not dry_run:
        _apply(ctx)
    return {"dry_run": dry_run, "changes": changes, "written": [] if dry_run else sorted(ctx.touched)}


def _apply(ctx):
    root = ctx.wiki.root
    for src, dst in ctx.moves:
        target = root / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        os.rename(str(root / src), str(target))
    for path in sorted(ctx.touched):
        meta, body = ctx.state[path]
        (root / path).write_text(render(meta, body), encoding="utf-8")
    ctx.wiki.invalidate()
```

In `toolkit/sb_core/cli.py` aggiungi `from .migrate import load_plan, migrate` e, prima di `COMMANDS`:

```python
def _add_migrate(sub, common):
    p = sub.add_parser("migrate", parents=[common], help="applica un piano di migrazione JSON")
    p.add_argument("plan", help="file JSON con {\"ops\": [...]}")
    p.add_argument("--dry-run", action="store_true", help="mostra le modifiche senza scrivere")
    p.set_defaults(handler=cmd_migrate)


def cmd_migrate(args):
    return migrate(_wiki(args), load_plan(args.plan), dry_run=args.dry_run), 0
```

Aggiorna: `COMMANDS = [_add_version, _add_validate, _add_index, _add_resolve, _add_tasks, _add_sources, _add_log, _add_lint, _add_status, _add_migrate]`

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core tests/test_migrate.py
git commit -m "feat(toolkit): atomic schema migrations with link rewriting"
```

---

### Task 11: `scaffold` e CLAUDE.md delle wiki

**Files:**
- Create: `toolkit/sb_core/scaffold.py`, `templates/wiki/CLAUDE.md`
- Modify: `toolkit/sb_core/cli.py` (comando `scaffold`)
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: `wiki.load_types`, `Wiki`, `index.write_index`, `log.LOG_HEADER`, `FORMAT_VERSION`, `errors.WikiError`
- Produces:
  - `scaffold.scaffold(schema_dir, target, template_dir=TEMPLATE_DIR) -> {"path", "types", "folders"}`. Valida lo schema **prima** di scrivere. Rifiuta una destinazione che contiene file diversi da `.git` e `.DS_Store`. Crea:
    - `schema/` (copia), più `schema/proposals.md` se manca;
    - una cartella con `.gitkeep` per ogni tipo, più `raw/`;
    - `CLAUDE.md`, `log.md`, `index.md`, `.sb/backlinks.json`;
    - `.gitignore` (`.sb/`, `.obsidian/workspace*.json`, `.DS_Store`) e `.obsidian/app.json`.
  - `scaffold.PROPOSALS_HEADER`.
  - CLI: `sb scaffold <schema-dir> <target>`, che non usa `--wiki`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_scaffold.py`:

```python
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import WikiCase, run_cli
from sb_core.errors import WikiError
from sb_core.scaffold import scaffold
from sb_core.validate import validate
from sb_core.wiki import Wiki


class ScaffoldTest(WikiCase):
    def setUp(self):
        self.schema = self.make_wiki() / "schema"
        self.base = Path(tempfile.mkdtemp(prefix="sb-target-"))
        self.addCleanup(shutil.rmtree, str(self.base), True)

    def test_creates_wiki(self):
        target = self.base / "wiki"
        result = scaffold(self.schema, target)
        for rel in ["CLAUDE.md", "schema/VERSION", "schema/proposals.md", "schema/types/task.md",
                    "knowledge/people/.gitkeep", "operations/tasks/.gitkeep", "outputs/briefings/.gitkeep",
                    "outputs/reports/.gitkeep", "raw/.gitkeep", "index.md", "log.md", ".gitignore",
                    ".obsidian/app.json", ".sb/backlinks.json"]:
            with self.subTest(rel=rel):
                self.assertTrue((target / rel).exists())
        self.assertIn(".sb/", (target / ".gitignore").read_text(encoding="utf-8"))
        self.assertIn("Second Brain", (target / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertFalse(json.loads((target / ".obsidian/app.json").read_text(encoding="utf-8"))["useMarkdownLinks"])
        self.assertIn("task", result["types"])
        self.assertIn("raw", result["folders"])
        self.assertEqual(validate(Wiki(target)), [])

    def test_accepts_folder_with_only_git(self):
        target = self.base / "clonata"
        (target / ".git").mkdir(parents=True)
        scaffold(self.schema, target)
        self.assertTrue((target / "schema" / "VERSION").is_file())

    def test_refuses_non_empty_target(self):
        target = self.base / "piena"
        target.mkdir()
        (target / "appunti.md").write_text("non toccare", encoding="utf-8")
        with self.assertRaises(WikiError):
            scaffold(self.schema, target)
        self.assertEqual(sorted(p.name for p in target.iterdir()), ["appunti.md"])

    def test_invalid_schema_writes_nothing(self):
        (self.schema / "types" / "task.md").unlink()
        target = self.base / "mai"
        with self.assertRaises(WikiError):
            scaffold(self.schema, target)
        self.assertFalse(target.exists())

    def test_cli(self):
        target = self.base / "cli"
        code, data, _ = run_cli("scaffold", self.schema, target)
        self.assertEqual((code, data["path"]), (0, str(target.resolve())))
        self.assertEqual(run_cli("scaffold", self.schema, target)[0], 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui i test e verifica che falliscano**

Run: `python3 -m unittest discover -s tests -p 'test_scaffold.py' -v`
Expected: ERROR `No module named 'sb_core.scaffold'`

- [ ] **Step 3: Implementa**

`templates/wiki/CLAUDE.md`:

```markdown
# Second Brain

Questa cartella è una wiki **Second Brain** gestita dal plugin Claude Code `sb`.
Prima di creare o modificare pagine leggi lo schema in `schema/`:
- i tipi di pagina (`schema/types/`);
- la semantica dei layer (`schema/layers.md`);
- le sorgenti esterne (`schema/sources.md`).

La prosa dei file di schema è vincolante.

## Comandi

`/sb:status` · `/sb:put` · `/sb:sync` · `/sb:ask` · `/sb:prep` · `/sb:report` · `/sb:tasks` · `/sb:lint` · `/sb:schema`

Si attivano anche in linguaggio naturale ("ho fatto l'1:1 con…", "preparami la riunione di…", "cosa devo fare oggi?").

## Mappa

- `knowledge/`: conoscenza stabile (persone, team, progetti, sistemi, processi, temi, fornitori, sintesi delle fonti). Si consolida.
- `operations/`: eventi e item datati (task, 1:1, meeting, decisioni, obiettivi, rischi). Si crea e si chiude.
- `outputs/`: briefing e report generati.
- `raw/`: sorgenti grezze catturate. **Immutabile.**
- `index.md`: indice generato, da non modificare a mano.
- `log.md`: registro delle operazioni, solo in aggiunta.

## Regole

- Nome del file = titolo. I wikilink puntano sempre al titolo canonico: `[[Titolo]]` o `[[Titolo|alias]]`.
- Nessun fatto senza fonte (`^[raw/…]`, `^[confluence:…]`, …) e nessun campo inventato.
- Mai modificare `raw/`.
- Le sezioni `## Note` raccolgono le opinioni dell'utente: un re-ingest non le sovrascrive mai.
- Le sorgenti esterne sono autorevoli sui fatti che documentano; la wiki ne è la rielaborazione strutturata.
- Ogni modifica termina con validate → index → log → commit → push.
- Le operazioni distruttive (spostamenti, merge, cancellazioni, migrazioni) richiedono una conferma esplicita e un commit dedicato.
- Dopo una modifica fatta a mano alle pagine, esegui `/sb:lint`.
```

`toolkit/sb_core/scaffold.py`:

```python
"""Creazione di una nuova wiki a partire da una cartella schema (es. un preset)."""
import json
import shutil
from pathlib import Path

from . import FORMAT_VERSION
from .errors import WikiError
from .index import write_index
from .log import LOG_HEADER
from .wiki import Wiki, load_types

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "wiki"
IGNORABLE = (".git", ".DS_Store")
GITIGNORE = ".sb/\n.obsidian/workspace*.json\n.DS_Store\n"
OBSIDIAN_APP = {
    "newLinkFormat": "shortest",
    "useMarkdownLinks": False,
    "alwaysUpdateLinks": True,
    "userIgnoreFilters": ["raw/", "schema/"],
}
PROPOSALS_HEADER = (
    "# Proposte di schema\n\n"
    "Una proposta per voce: `- [ ] P<n> · <titolo>` con sotto-voci `- segnale:` e `- proposta:`.\n"
    "`- [x]` = applicata, `- [-]` = scartata (con il motivo).\n\n"
)


def scaffold(schema_dir, target, template_dir=TEMPLATE_DIR):
    schema_dir, target = Path(schema_dir), Path(target)
    version_file = schema_dir / "VERSION"
    if not version_file.is_file():
        raise WikiError(f"{schema_dir} non è una cartella schema (manca VERSION)")
    if version_file.read_text(encoding="utf-8").strip() != str(FORMAT_VERSION):
        raise WikiError(f"lo schema deve essere in formato {FORMAT_VERSION}")
    types = load_types(schema_dir)
    if target.exists() and any(p.name not in IGNORABLE for p in target.iterdir()):
        raise WikiError(f"{target} esiste e non è vuota: scegli un'altra cartella")
    template = Path(template_dir) / "CLAUDE.md"
    if not template.is_file():
        raise WikiError(f"template mancante: {template}")

    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(schema_dir), str(target / "schema"))
    proposals = target / "schema" / "proposals.md"
    if not proposals.exists():
        proposals.write_text(PROPOSALS_HEADER, encoding="utf-8")
    folders = sorted({t.folder for t in types.values()} | {"raw"})
    for folder in folders:
        directory = target / folder
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ".gitkeep").write_text("", encoding="utf-8")
    shutil.copyfile(str(template), str(target / "CLAUDE.md"))
    (target / "log.md").write_text(LOG_HEADER, encoding="utf-8")
    (target / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (target / ".obsidian").mkdir(exist_ok=True)
    (target / ".obsidian" / "app.json").write_text(json.dumps(OBSIDIAN_APP, indent=2) + "\n", encoding="utf-8")
    write_index(Wiki(target))
    return {"path": str(target.resolve()), "types": sorted(types), "folders": folders}
```

In `toolkit/sb_core/cli.py` aggiungi `from .scaffold import scaffold` e, prima di `COMMANDS`:

```python
def _add_scaffold(sub, common):
    p = sub.add_parser("scaffold", help="crea una nuova wiki da una cartella schema")
    p.add_argument("schema_dir", help="cartella schema (es. presets/head-of-engineering)")
    p.add_argument("target", help="cartella della nuova wiki (vuota o con solo .git)")
    p.set_defaults(handler=cmd_scaffold)


def cmd_scaffold(args):
    return scaffold(args.schema_dir, args.target), 0
```

Aggiorna: `COMMANDS = [_add_version, _add_validate, _add_index, _add_resolve, _add_tasks, _add_sources, _add_log, _add_lint, _add_status, _add_migrate, _add_scaffold]`

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core templates tests/test_scaffold.py
git commit -m "feat(toolkit): scaffold new wikis from a schema folder"
```

---

### Task 12: Preset `head-of-engineering`

**Files:**
- Create: `presets/head-of-engineering/VERSION`, `layers.md`, `sources.md`
- Create: `presets/head-of-engineering/types/{person,team,project,system,process,topic,vendor,source-note,task,one-on-one,meeting,decision,goal,risk}.md`
- Create: `presets/head-of-engineering/briefings/{one-on-one,meeting,person,project}.md`
- Create: `presets/head-of-engineering/reports/{week,month,risks,load,upward,delegated}.md`
- Test: `tests/test_preset.py`

**Interfaces:**
- Consumes: `wiki.load_types`, `scaffold.scaffold`, `validate.validate`, `lint.lint`, `frontmatter.parse`
- Produces: una cartella schema completa, usata da `/sb:init` (Task 13) e dalla wiki di esempio (Task 17). I nomi dei campi usati dalle skill e dal toolkit sono: `one-on-one.with`, `one-on-one.date`, i campi `task.*`, `meeting.date`, `person.relationship`.

- [ ] **Step 1: Scrivi il test che fallisce**

`tests/test_preset.py`:

```python
import datetime
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT
from sb_core.frontmatter import parse
from sb_core.lint import lint
from sb_core.scaffold import scaffold
from sb_core.validate import validate
from sb_core.wiki import DEFAULT_THRESHOLDS, Wiki, load_types

PRESET = ROOT / "presets" / "head-of-engineering"
EXPECTED = {
    "knowledge": {"person", "team", "project", "system", "process", "topic", "vendor", "source-note"},
    "operations": {"task", "one-on-one", "meeting", "decision", "goal", "risk"},
}


class PresetTest(unittest.TestCase):
    def test_types_by_layer(self):
        by_layer = {}
        for typedef in load_types(PRESET).values():
            if not typedef.builtin:
                by_layer.setdefault(typedef.layer, set()).add(typedef.name)
        self.assertEqual(by_layer, EXPECTED)

    def test_every_type_has_guidance(self):
        for path in sorted((PRESET / "types").glob("*.md")):
            with self.subTest(type=path.stem):
                meta, body = parse(path.read_text(encoding="utf-8"))
                self.assertEqual(meta["name"], path.stem)
                for marker in ("**Crea**", "**Non creare**", "**Struttura del corpo**"):
                    self.assertIn(marker, body)

    def test_contracts_used_by_toolkit_and_skills(self):
        types = load_types(PRESET)
        task = types["task"].fields
        for field in ("status", "owner", "due", "priority", "related"):
            self.assertIn(field, task)
        self.assertEqual(task["status"]["closed"], ["done", "dropped"])
        self.assertEqual(task["owner"], {"kind": "link", "to": "person"})
        self.assertEqual(types["one-on-one"].required, ["with", "date"])
        self.assertEqual(types["one-on-one"].fields["with"], {"kind": "link", "to": "person"})

    def test_templates(self):
        self.assertEqual(sorted(p.stem for p in (PRESET / "briefings").glob("*.md")),
                         ["meeting", "one-on-one", "person", "project"])
        self.assertEqual(sorted(p.stem for p in (PRESET / "reports").glob("*.md")),
                         ["delegated", "load", "month", "risks", "upward", "week"])

    def test_scaffolds_a_clean_wiki(self):
        tmp = Path(tempfile.mkdtemp(prefix="sb-preset-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        scaffold(PRESET, tmp / "wiki")
        wiki = Wiki(tmp / "wiki")
        self.assertEqual(validate(wiki), [])
        self.assertEqual(lint(wiki, datetime.date.today()), [])
        self.assertEqual(wiki.sources, {})
        self.assertEqual(wiki.thresholds, DEFAULT_THRESHOLDS)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Esegui il test e verifica che fallisca**

Run: `python3 -m unittest discover -s tests -p 'test_preset.py' -v`
Expected: ERROR `WikiError: manca la cartella …/presets/head-of-engineering/types`

- [ ] **Step 3: Crea i file del preset**

`presets/head-of-engineering/VERSION`:

```
1
```

`presets/head-of-engineering/layers.md`:

```markdown
---
stale_operations_days: 30
one_on_one_gap_days: 21
due_soon_days: 7
---
# Layer

## knowledge

Conoscenza che cambia lentamente: chi sono le persone e come sono fatti team, progetti, sistemi e processi; quali sono i temi ricorrenti.

- Le pagine si **aggiornano e consolidano**: sezioni stabili, frasi riscritte quando i fatti cambiano, nessun diario.
- Una pagina knowledge descrive lo stato attuale. La storia si ricostruisce dalle pagine operations collegate.
- Il lint cerca contraddizioni e pagine da consolidare.

## operations

Eventi e item datati: task, 1:1, meeting, decisioni, obiettivi, rischi.

- Le pagine si **creano, si chiudono e restano**: si chiudono con `status`, non si cancellano.
- Gli eventi hanno titoli datati: `AAAA-MM-GG <descrizione>`.
- Il lint segnala i task scaduti e gli item aperti fermi da più di `stale_operations_days` giorni.

## outputs

Briefing e report generati da `/sb:prep` e `/sb:report`. Sono fotografie datate: si rigenerano nello stesso giorno, non si modificano dopo.

## Propagazione

Un'informazione operativa che cambia la conoscenza stabile aggiorna anche la pagina knowledge e la collega. Esempi:
- una decisione presa in un meeting aggiorna la pagina del progetto;
- un cambio di ruolo emerso in un 1:1 aggiorna la pagina della persona.

## Soglie

- `stale_operations_days`: giorni senza aggiornamenti dopo cui un item operativo aperto è considerato fermo.
- `one_on_one_gap_days`: giorni senza 1:1 dopo cui `/sb:status` segnala la persona (cadenza abituale + margine).
- `due_soon_days`: orizzonte di "in scadenza" per `/sb:status` e per la vista `week`.
```

`presets/head-of-engineering/sources.md`:

```markdown
---
sources: {}
---
# Sorgenti esterne

Registro delle knowledge base esterne. Una sorgente esterna è **autorevole sui fatti** che documenta. La wiki ne conserva una sintesi (`source-note`) e propaga i fatti nelle pagine tipizzate, sempre con citazione.

Ogni sorgente è una riga nel frontmatter:

    sources:
      conf-eng: {system: confluence, scope: ENG, covers: [process, system], stale_after_days: 30}
      jira-plat: {system: jira, scope: PLAT, covers: [project], stale_after_days: 14}

- `system`: `confluence`, `jira` o un altro sistema raggiungibile via MCP.
- `scope`: chiave dello spazio o del progetto (`ENG` in `confluence:ENG/123`, `PLAT` in `jira:PLAT-42`).
- `covers`: tipi di pagina che vivono soprattutto in questa sorgente.
- `stale_after_days`: dopo quanti giorni una source-note va ricontrollata con `/sb:sync`.

Link web (`url:`) e mail (`mail:`) non si registrano: sono catture una tantum.

Sotto, una sezione per ogni sorgente: a cosa serve, chi la mantiene, cosa ingerire e cosa no.
```

`presets/head-of-engineering/types/person.md`:

```markdown
---
name: person
layer: knowledge
folder: knowledge/people
fields:
  role: {kind: string}
  relationship: {kind: enum, values: [report, skip-report, peer, manager, stakeholder, external]}
  team: {kind: link, to: team}
  reports_to: {kind: link, to: person}
  status: {kind: enum, values: [active, left], closed: [left]}
---
# Person

Una persona con cui lavori: riporti diretti e indiretti, peer, il tuo manager, stakeholder, contatti esterni.

**Crea** una pagina quando una persona compare in modo ricorrente o ha un ruolo attivo in un progetto, una decisione, un task o un 1:1.

**Non creare** una pagina per menzioni di passaggio: scrivi solo il nome nel testo, senza link.

**Struttura del corpo** (si aggiorna e si consolida, non si accoda):
- `## Ruolo e contesto`: cosa fa, in quale team, da quanto, punti di forza.
- `## Obiettivi e crescita`: aspirazioni, piano di sviluppo, feedback, ognuno con data e fonte.
- `## Temi aperti`: questioni in corso, ognuna collegata alla pagina operativa (1:1, task, rischio).
- `## Note`: osservazioni e valutazioni dell'utente. Il re-ingest non le tocca mai.

`relationship` è il rapporto con l'utente. La cronologia degli incontri sta nelle pagine `one-on-one` e `meeting`. Quando una persona lascia l'azienda, imposta `status: left` e non cancellare la pagina.
```

`presets/head-of-engineering/types/team.md`:

```markdown
---
name: team
layer: knowledge
folder: knowledge/teams
fields:
  lead: {kind: link, to: person}
  parent: {kind: link, to: team}
  status: {kind: enum, values: [active, dissolved], closed: [dissolved]}
---
# Team

Un team o un'unità organizzativa: squadre di prodotto, piattaforma, chapter, gruppi trasversali.

**Crea** una pagina per ogni team che riporta a te, che dipende da te o con cui collabori stabilmente.

**Non creare** pagine per gruppi temporanei di una sola riunione: quelli sono `meeting`.

**Struttura del corpo**:
- `## Missione e perimetro`: di cosa si occupa, quali sistemi e progetti possiede (con link).
- `## Persone`: membri e ruoli, con link alle pagine `person`.
- `## Modo di lavorare`: rituali, on-call, metriche seguite.
- `## Salute`: carico, morale, rischi ricorrenti, con link a `risk` e `one-on-one`.
- `## Note`: valutazioni dell'utente.
```

`presets/head-of-engineering/types/project.md`:

```markdown
---
name: project
layer: knowledge
folder: knowledge/projects
fields:
  status: {kind: enum, values: [proposed, active, paused, done, cancelled], closed: [done, cancelled]}
  owner: {kind: link, to: person}
  team: {kind: link, to: team}
  systems: {kind: list, of: link, to: system}
  start: {kind: date}
  target: {kind: date}
---
# Project

Un'iniziativa con un obiettivo, un responsabile e una durata: progetti di prodotto, migrazioni, programmi trasversali.

**Crea** una pagina quando un'iniziativa ha un nome riconosciuto e compare in più conversazioni o documenti.

**Non creare** pagine per attività di pochi giorni: quelle sono `task`.

**Struttura del corpo**:
- `## Obiettivo`: perché esiste, cosa cambia quando è finito.
- `## Perimetro e architettura`: cosa include ed esclude, sistemi coinvolti (con link).
- `## Stato`: sintesi attuale in 2–4 righe, riscritta a ogni aggiornamento. La cronologia sta in `decision`, `meeting` e `risk`.
- `## Stakeholder`: persone e team coinvolti.
- `## Note`: valutazioni dell'utente.
```

`presets/head-of-engineering/types/system.md`:

```markdown
---
name: system
layer: knowledge
folder: knowledge/systems
fields:
  owner_team: {kind: link, to: team}
  criticality: {kind: enum, values: [low, medium, high]}
  status: {kind: enum, values: [active, deprecated, retired], closed: [retired]}
---
# System

Un sistema tecnico: servizio, applicazione, piattaforma, componente infrastrutturale.

**Crea** una pagina per i sistemi che compaiono in decisioni, rischi, incidenti o progetti.

**Non creare** pagine per librerie o componenti interni senza rilevanza manageriale.

**Struttura del corpo**:
- `## Cosa fa`: in 2–3 righe, per chi lo usa.
- `## Architettura`: dipendenze principali e tecnologie, con link ad altri `system`.
- `## Responsabilità`: team owner, on-call, contatti.
- `## Stato e debito tecnico`: problemi noti, con link a `risk` e `decision`.
- `## Note`: valutazioni dell'utente.
```

`presets/head-of-engineering/types/process.md`:

```markdown
---
name: process
layer: knowledge
folder: knowledge/processes
fields:
  owner: {kind: link, to: person}
  cadence: {kind: string}
---
# Process

Un modo di lavorare codificato: rituali, policy, playbook (incident management, hiring loop, planning, performance review).

**Crea** una pagina quando un processo viene citato come riferimento o ne discuti il funzionamento.

**Non creare** pagine per una singola istanza del processo: quella è un `meeting` o un `task`.

**Struttura del corpo**:
- `## Scopo`: a cosa serve.
- `## Come funziona`: passi essenziali. Il dettaglio resta alla fonte, se il processo è documentato in Confluence.
- `## Ruoli`: chi fa cosa.
- `## Problemi noti`: cosa non funziona, con link alle fonti.
- `## Note`: valutazioni dell'utente.
```

`presets/head-of-engineering/types/topic.md`:

```markdown
---
name: topic
layer: knowledge
folder: knowledge/topics
---
# Topic

Un tema ricorrente che attraversa persone e progetti: hiring, budget, tech debt, on-call, career framework, AI adoption.

**Crea** una pagina quando un tema emerge in almeno due contesti diversi (1:1, meeting, documenti).

**Non creare** un topic per entità che hanno un tipo dedicato: persone, team, progetti, sistemi, fornitori. Se un topic finisce per descrivere sempre lo stesso genere di cosa, registra un segnale di schema.

**Struttura del corpo**:
- `## Di cosa si tratta`: definizione nel contesto dell'organizzazione.
- `## Stato attuale`: situazione in 2–5 righe.
- `## Dove emerge`: link alle pagine operations più rilevanti, dalla più recente.
- `## Note`: valutazioni dell'utente.
```

`presets/head-of-engineering/types/vendor.md`:

```markdown
---
name: vendor
layer: knowledge
folder: knowledge/vendors
fields:
  contact: {kind: link, to: person}
  contract_end: {kind: date}
  status: {kind: enum, values: [evaluating, active, ended], closed: [ended]}
---
# Vendor

Un fornitore esterno: software, servizi, consulenza, staffing.

**Crea** una pagina quando un fornitore ha un contratto attivo o è in valutazione.

**Non creare** pagine per strumenti usati senza un rapporto commerciale da gestire.

**Struttura del corpo**:
- `## Cosa forniscono`: servizio, perimetro, team che lo usano.
- `## Contratto`: scadenze, rinnovi, costi se noti (con fonte).
- `## Rapporto`: qualità, problemi, escalation, con link alle pagine operations.
- `## Note`: valutazioni dell'utente.
```

`presets/head-of-engineering/types/source-note.md`:

```markdown
---
name: source-note
layer: knowledge
folder: knowledge/sources
---
# Source note

La sintesi di un documento esterno o di una cattura: pagina Confluence, ticket Jira, thread mail, articolo web. È il ponte tra la sorgente e le pagine tipizzate.

**Crea** una source-note per ogni documento esterno ingerito, una sola per riferimento `external`.

**Non creare** source-note per le catture conservate in `raw/` (dettati, file locali): il grezzo è già la fonte.

**Struttura del corpo**:
- `## Sintesi`: 5–20 righe sui punti rilevanti per il management.
- `## Pagine collegate`: le pagine tipizzate in cui sono stati propagati i fatti.

Campi comuni obbligatori nella pratica:
- `external`: riferimento alla sorgente;
- `version`: versione della pagina, `updated` del ticket, data dell'ultimo messaggio;
- `synced`: data dell'ultimo allineamento.

Titolo: `<Sistema> · <titolo del documento>`. Con `authority: migrated` la wiki diventa fonte di verità e la sorgente non si re-ingerisce più.
```

`presets/head-of-engineering/types/task.md`:

```markdown
---
name: task
layer: operations
folder: operations/tasks
fields:
  status: {kind: enum, values: [todo, doing, blocked, done, dropped], closed: [done, dropped]}
  owner: {kind: link, to: person}
  due: {kind: date}
  priority: {kind: enum, values: [low, medium, high]}
  related: {kind: list, of: link}
---
# Task

Un'azione concreta da fare: tua, oppure delegata a qualcuno e da tenere d'occhio.

**Crea** un task per ogni impegno esplicito:
- dell'utente: "devo…", "mi prendo…", "entro venerdì mando…";
- di un'altra persona verso l'utente: "Luca mi manda…", "ho chiesto ad Anna di…".

**Non creare** task per intenzioni vaghe ("prima o poi…") o per attività del team che non richiedono di essere seguite dall'utente: quelle stanno nel tool del team.

**Struttura del corpo**: 1–3 righe di contesto con citazione, poi una riga datata per ogni aggiornamento (`- AAAA-MM-GG: …`).

Regole per i campi, tutti opzionali e da inferire solo con ragionevole sicurezza:
- `title`: verbo all'infinito, specifico ("Mandare a Luca la proposta di budget Q4").
- `owner`: solo se l'azione è di un'altra persona. Senza owner il task è dell'utente: non mettere mai l'utente come owner.
- `due`: data assoluta, calcolata rispetto alla data dell'evento d'origine.
- `priority`: solo con segnali espliciti (urgente, bloccante = high; quando puoi = low).
- `status`: `todo` di default; `doing` e `blocked` solo se dichiarati.
- `related`: evento d'origine ed entità coinvolte.
```

`presets/head-of-engineering/types/one-on-one.md`:

```markdown
---
name: one-on-one
layer: operations
folder: operations/one-on-ones
fields:
  with: {kind: link, to: person}
  date: {kind: date}
required: [with, date]
---
# One-on-one

Un incontro individuale ricorrente tra l'utente e una persona.

**Crea** una pagina per ogni 1:1 di cui l'utente racconta o condivide le note. Titolo: `AAAA-MM-GG 1on1 <Nome Cognome>`.

**Non creare** un one-on-one per incontri a più persone (sono `meeting`) o per scambi rapidi senza contenuto.

**Struttura del corpo**:
- `## Temi`: punti discussi, con link a persone, progetti e topic.
- `## Umore e segnali`: stato d'animo, preoccupazioni, segnali di rischio (retention, burnout), riportati come l'utente li ha descritti.
- `## Impegni`: link ai task creati in entrambe le direzioni.
- `## Note`: valutazioni dell'utente.

Propaga nella pagina `person` solo ciò che cambia la conoscenza stabile (ruolo, aspirazioni, piano di crescita).
```

`presets/head-of-engineering/types/meeting.md`:

```markdown
---
name: meeting
layer: operations
folder: operations/meetings
fields:
  date: {kind: date}
  series: {kind: string}
  attendees: {kind: list, of: link, to: person}
  project: {kind: link, to: project}
required: [date]
---
# Meeting

Una riunione con più partecipanti: staff meeting, review, planning, incontri con stakeholder, incident review.

**Crea** una pagina per ogni riunione con contenuto rilevante (decisioni, task, informazioni nuove). Titolo: `AAAA-MM-GG <nome della riunione>`. `series` raggruppa le ricorrenze (es. `Weekly Platform`).

**Non creare** pagine per riunioni senza contenuto da ricordare.

**Struttura del corpo**:
- `## Contesto`: perché si è tenuta.
- `## Punti`: cosa è emerso, con link.
- `## Decisioni`: link alle pagine `decision` create.
- `## Azioni`: link ai task creati.
- `## Note`: valutazioni dell'utente.
```

`presets/head-of-engineering/types/decision.md`:

```markdown
---
name: decision
layer: operations
folder: operations/decisions
fields:
  date: {kind: date}
  status: {kind: enum, values: [proposed, accepted, rejected, superseded], closed: [accepted, rejected, superseded]}
  decided_by: {kind: list, of: link, to: person}
  project: {kind: link, to: project}
  supersedes: {kind: link, to: decision}
---
# Decision

Una decisione rilevante, nello stile di un ADR leggero: tecnica, organizzativa, di priorità.

**Crea** una pagina quando viene presa o proposta una decisione che qualcuno vorrà ritrovare ("perché abbiamo scelto X?"). Titolo: `AAAA-MM-GG <decisione in breve>`.

**Non creare** pagine per scelte operative minori senza impatto oltre la settimana.

**Struttura del corpo**:
- `## Contesto`: il problema e i vincoli.
- `## Decisione`: cosa si è deciso.
- `## Alternative considerate`: con il motivo per cui sono state scartate.
- `## Conseguenze`: cosa cambia; aggiorna anche le pagine knowledge interessate.
- `## Note`: valutazioni dell'utente.

Quando una decisione ne sostituisce un'altra: `supersedes` sulla nuova e `status: superseded` sulla vecchia.
```

`presets/head-of-engineering/types/goal.md`:

```markdown
---
name: goal
layer: operations
folder: operations/goals
fields:
  period: {kind: string}
  status: {kind: enum, values: [planned, on-track, at-risk, off-track, achieved, missed, dropped], closed: [achieved, missed, dropped]}
  owner: {kind: link, to: person}
  project: {kind: link, to: project}
---
# Goal

Un obiettivo con un periodo: OKR, obiettivi di team o personali, impegni presi con il proprio manager.

**Crea** una pagina per ogni obiettivo formalizzato. `period` usa la forma `AAAA-Qn` o `AAAA`.

**Non creare** obiettivi per desideri non concordati: quelli vanno nelle `## Note` di una persona o di un team.

**Struttura del corpo**:
- `## Obiettivo e risultati chiave`: cosa, come si misura.
- `## Avanzamento`: una riga datata per ogni aggiornamento, con fonte.
- `## Rischi`: link alle pagine `risk`.
- `## Note`: valutazioni dell'utente.
```

`presets/head-of-engineering/types/risk.md`:

```markdown
---
name: risk
layer: operations
folder: operations/risks
fields:
  status: {kind: enum, values: [open, mitigating, closed, accepted], closed: [closed, accepted]}
  likelihood: {kind: enum, values: [low, medium, high]}
  impact: {kind: enum, values: [low, medium, high]}
  owner: {kind: link, to: person}
  project: {kind: link, to: project}
  review: {kind: date}
---
# Risk

Un rischio da seguire: delivery, persone (retention, burnout, single point of failure), tecnico, di fornitore, di budget.

**Crea** una pagina quando un rischio viene nominato esplicitamente o emerge con chiarezza da più segnali.

**Non creare** pagine per preoccupazioni generiche senza un oggetto preciso.

**Struttura del corpo**:
- `## Descrizione`: cosa può succedere e perché.
- `## Segnali`: evidenze datate con fonte.
- `## Mitigazioni`: azioni in corso, con link ai task.
- `## Note`: valutazioni dell'utente.

`likelihood` e `impact` vanno valorizzati solo se dichiarati o deducibili con chiarezza. `review` è la prossima data di revisione.
```

`presets/head-of-engineering/briefings/one-on-one.md`:

```markdown
# Briefing 1:1

Si usa con `/sb:prep <persona>` quando con la persona esistono pagine `one-on-one`. Finestra: ultimi 90 giorni.

1. **Dall'ultima volta**: data dell'ultimo 1:1, temi principali, impegni presi da entrambi e il loro stato.
2. **Task aperti**: i tuoi verso la persona (senza owner, con la persona in `related`) e i suoi verso di te (owner = persona). Evidenzia gli scaduti.
3. **Temi ricorrenti**: argomenti emersi in almeno due degli ultimi 1:1.
4. **Contesto recente**: decisioni, rischi, meeting e novità sui suoi progetti e sul suo team.
5. **Crescita**: obiettivi e piano di sviluppo dalla pagina `person`.
6. **Domande suggerite**: 3–5, collegate ai punti sopra.
```

`presets/head-of-engineering/briefings/meeting.md`:

```markdown
# Briefing riunione

Si usa con `/sb:prep <meeting o serie>`. Finestra: ultime 3 occorrenze della stessa `series`, oppure 60 giorni.

1. **Scopo e partecipanti**: dalla serie o dall'invito, con link alle persone.
2. **Dall'ultima volta**: decisioni prese e azioni aperte (task in `related`).
3. **Novità rilevanti**: cambiamenti nei progetti, sistemi e rischi collegati.
4. **Punti da portare**: proposte dell'utente, con motivazione e fonte.
5. **Domande aperte**: cosa serve decidere o chiarire.
```

`presets/head-of-engineering/briefings/person.md`:

```markdown
# Briefing persona

Si usa con `/sb:prep <persona>` quando non ci sono 1:1 con quella persona (peer, stakeholder, contatti esterni). Finestra: ultimi 180 giorni.

1. **Chi è**: ruolo, team, rapporto con l'utente.
2. **Interazioni recenti**: meeting, decisioni e documenti in cui compare.
3. **Impegni aperti**: task in entrambe le direzioni.
4. **Interessi e posizioni**: cosa le sta a cuore, posizioni espresse (con fonte).
5. **Come affrontare l'incontro**: 2–3 suggerimenti basati sui punti sopra.
```

`presets/head-of-engineering/briefings/project.md`:

```markdown
# Briefing progetto o team

Si usa con `/sb:prep <progetto | team>`. Finestra: ultimi 60 giorni.

1. **Sintesi**: obiettivo e stato attuale, dalla pagina knowledge.
2. **Cosa è cambiato**: decisioni, meeting e aggiornamenti delle sorgenti nella finestra.
3. **Rischi aperti**: con likelihood, impact e owner.
4. **Task aperti**: tuoi e delegati, scaduti in evidenza.
5. **Persone**: chi sta lavorando su cosa, segnali di carico.
6. **Prossimi passi suggeriti**: 3–5.
```

`presets/head-of-engineering/reports/week.md`:

```markdown
# Report settimanale

`/sb:report week`. Periodo di default: ultimi 7 giorni.

1. **In evidenza**: le 3–5 cose più importanti successe.
2. **Decisioni**: prese o proposte nel periodo.
3. **Persone**: 1:1 fatti e segnali emersi.
4. **Task**: chiusi, aperti nel periodo, scaduti.
5. **Rischi**: nuovi o cambiati.
6. **Prossima settimana**: scadenze e appuntamenti noti.
```

`presets/head-of-engineering/reports/month.md`:

```markdown
# Report mensile

`/sb:report month`. Periodo di default: mese corrente fino a oggi; `--period AAAA-MM` per un mese chiuso.

1. **Sintesi del mese**: 5–8 righe.
2. **Progetti**: avanzamento per progetto, con decisioni chiave.
3. **Persone e team**: cambiamenti, crescita, segnali di rischio.
4. **Obiettivi**: stato dei `goal` del periodo.
5. **Rischi**: aperti, chiusi, cambiati.
6. **Temi ricorrenti**: topic emersi più volte.
```

`presets/head-of-engineering/reports/risks.md`:

```markdown
# Report rischi

`/sb:report risks [--scope <progetto | team>]`. Periodo di default: tutti i rischi aperti, più quelli chiusi negli ultimi 30 giorni.

1. **Mappa**: tabella con rischio · likelihood · impact · owner · stato · prossima revisione.
2. **Da guardare subito**: high/high, revisioni scadute, rischi senza owner.
3. **Cambiamenti recenti**: nuovi segnali e mitigazioni.
4. **Pattern**: rischi simili su più progetti o team.
```

`presets/head-of-engineering/reports/load.md`:

```markdown
# Report carico del team

`/sb:report load [--scope <team>]`. Periodo di default: ultimi 30 giorni.

1. **Per persona**: progetti attivi, task delegati aperti, segnali emersi nei 1:1 (carico, on-call, stanchezza), con fonte.
2. **Concentrazioni**: persone su troppi progetti, single point of failure.
3. **Segnali di rischio**: rischi di tipo persone aperti.
4. **Proposte**: ribilanciamenti possibili, con motivazione.
```

`presets/head-of-engineering/reports/upward.md`:

```markdown
# Report per il proprio manager

`/sb:report upward`. Periodo di default: dall'ultimo report `upward` in `outputs/reports/`, oppure ultimi 14 giorni.

Tono sintetico e orientato ai risultati; nessun dettaglio personale emerso nei 1:1.

1. **Highlights**: risultati raggiunti.
2. **In corso**: stato dei progetti principali (verde, giallo o rosso, con motivo).
3. **Rischi e blocchi**: cosa serve dal manager.
4. **Decisioni prese**: con impatto.
5. **Prossimi passi**.
```

`presets/head-of-engineering/reports/delegated.md`:

```markdown
# Report delegati

`/sb:report delegated [--scope <persona | progetto>]`. Periodo: tutti i task delegati aperti.

1. **Per persona**: task con scadenza e stato; scaduti in evidenza.
2. **Senza scadenza**: delegati senza `due` da più di 14 giorni.
3. **Bloccati**: con il motivo, se noto.
4. **Suggerimenti**: solleciti da fare, da portare nel prossimo 1:1.
```

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Commit**

```bash
git add presets tests/test_preset.py
git commit -m "feat: head-of-engineering preset schema"
```

---

### Task 13: Convenzioni comuni, skill `init` e `status`

**Files:**
- Create: `references/conventions.md`, `skills/init/SKILL.md`, `skills/status/SKILL.md`
- Modify: `tests/test_plugin_layout.py` (aggiunge `SkillsTest`)

**Interfaces:**
- Consumes: i comandi del toolkit `version`, `scaffold`, `validate`, `index`, `log`, `resolve`, `status`; il preset (Task 12); `templates/wiki/CLAUDE.md`.
- Produces:
  - `references/conventions.md`, letto da tutte le skill. Definisce:
    - `SB` = `python3 "<BASE>/../../toolkit/sb.py"`;
    - il flusso di chiusura validate → index → log → commit `sb(<skill>): …` → push;
    - le regole di ambiguità con `resolve`;
    - il formato delle proposte di schema.
  - Skill `/sb:init` e `/sb:status`.

- [ ] **Step 1: Scrivi il test che fallisce**

Aggiungi a `tests/test_plugin_layout.py` (e `from sb_core.frontmatter import parse` agli import):

```python
SKILLS_DIR = ROOT / "skills"


class SkillsTest(unittest.TestCase):
    def test_conventions_exist(self):
        text = (ROOT / "references" / "conventions.md").read_text(encoding="utf-8")
        for marker in ("toolkit/sb.py", "Flusso di chiusura", "sb(", "Ambiguità", "proposals.md"):
            self.assertIn(marker, text)

    def test_skills_are_well_formed(self):
        files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(skill=path.parent.name):
                meta, body = parse(path.read_text(encoding="utf-8"))
                self.assertEqual(meta["name"], path.parent.name)
                self.assertGreater(len(meta["description"]), 60)
                self.assertIn("references/conventions.md", body)
                self.assertNotIn("```", body, "le skill usano blocchi indentati, non recinti")
```

- [ ] **Step 2: Esegui il test e verifica che fallisca**

Run: `python3 -m unittest discover -s tests -p 'test_plugin_layout.py' -v`
Expected: FAIL/ERROR su `test_conventions_exist` (file mancante) e `test_skills_are_well_formed` (`files` vuoto)

- [ ] **Step 3: Scrivi le convenzioni e le due skill**

`references/conventions.md`:

````markdown
# Convenzioni comuni delle skill `sb`

Ogni skill del plugin legge questo file prima di agire. BASE è la *base directory* della skill, indicata quando la skill viene caricata. La radice del plugin è `BASE/../..`.

## Toolkit

    SB = python3 "BASE/../../toolkit/sb.py"

- Ogni comando stampa JSON su stdout. Exit `0` = ok; `1` = problemi trovati, descritti nel JSON; `2` = errore d'uso o d'ambiente (leggi il campo `error`).
- Si lancia dalla radice della wiki o da una sua sottocartella. Altrimenti si passa `--wiki <cartella>`.
- `SB version` ritorna `wiki`: il percorso della wiki corrente, oppure `null` se non sei in una wiki. In quel caso, per ogni comando tranne `init`, fermati e proponi `/sb:init`.
- Non rifare a mano ciò che fa il toolkit: validazione, indice, risoluzione dei nomi, query sui task, sorgenti stantie, lint strutturale, migrazioni, log.

| Comando | Uso |
|---|---|
| `SB validate [pagine…]` | Controlla le pagine contro lo schema |
| `SB index` | Rigenera `index.md` e `.sb/backlinks.json` |
| `SB resolve "<nome>" [--type T]` | Trova le pagine candidate per un nome |
| `SB tasks list --view V [--project P] [--person P] [--priority X]` | Elenca i task (viste: mine, delegated, overdue, today, week, blocked, all) |
| `SB sources stale` | Elenca le source-note da riallineare |
| `SB lint` | Esegue i controlli strutturali |
| `SB status` | Raccoglie i dati del cruscotto |
| `SB migrate <piano.json> [--dry-run]` | Esegue spostamenti, retitle, rinomina e modifica di campi |
| `SB log "<messaggio>" --op <skill>` | Aggiunge una riga a `log.md` |
| `SB scaffold <schema-dir> <cartella>` | Crea una nuova wiki |

## Prima di scrivere

Leggi `schema/layers.md`, i file `schema/types/<tipo>.md` dei tipi che userai e `schema/sources.md` se tocchi sorgenti esterne. La prosa dei tipi è vincolante: dice quando creare una pagina, quando non crearla e come strutturarne il corpo.

## Formato delle pagine

- Nome del file = `title` + `.md`, nella cartella `folder` del tipo. I titoli non contengono `\ / : * ? " < > | # ^ [ ]`: scrivi "1on1" e non "1:1", usa "·" o "-" come separatori.
- I wikilink puntano sempre al titolo canonico: `[[Luca Bianchi]]`, oppure `[[Luca Bianchi|Luca]]` per mostrare un alias. Nel frontmatter i link vanno tra virgolette: `owner: "[[Luca Bianchi]]"`, `related: ["[[A]]", "[[B]]"]`.
- Le date sono in formato ISO `AAAA-MM-GG`. Converti sempre le espressioni relative ("venerdì", "fine mese") rispetto alla data dell'evento.
- Metti tra virgolette le stringhe del frontmatter che contengono `, ` `: ` ` #` o che iniziano con un simbolo.
- Citazioni: ogni fatto rilevante porta `^[<fonte>]`, dove fonte è il percorso di un file in `raw/` senza `.md` (`raw/2026/10/2026-10-02-1on1-luca`) o un riferimento esterno (`confluence:ENG/123`, `jira:PLAT-42`, `url:https://…`, `mail:<id>`). Le stesse fonti vanno nella lista `sources` del frontmatter.
- `created` va impostato alla creazione, `updated` a ogni modifica sostanziale.

## Ambiguità

Per ogni entità menzionata esegui `SB resolve "<nome>"`.

- Un candidato con `match` `title` o `alias` è quello giusto: usalo.
- Un solo candidato `partial` (punteggio 0.75) e nessun altro sopra 0.5: usalo.
- Più candidati, oppure solo `fuzzy`: chiedi all'utente con una sola domanda a scelta multipla, includendo l'opzione "nuova pagina". Poi aggiungi il nome usato agli `aliases` della pagina scelta.
- Nessun candidato: è un'entità nuova. Creala solo se la prosa del tipo lo prevede; altrimenti scrivi il nome come testo semplice.

## Regole non negoziabili

- Nessun fatto senza fonte. Nessun campo inventato: se non è inferibile con ragionevole sicurezza, omettilo.
- Mai modificare i file in `raw/` dopo la cattura.
- Le sezioni `## Note` raccolgono opinioni e valutazioni dell'utente: un re-ingest non le sovrascrive mai.
- Le source-note con `authority: migrated` non si re-ingeriscono.
- Un task dell'utente non ha `owner`. `owner` indica solo un'altra persona.
- Se una fonte esterna non è raggiungibile (tool MCP assente o in errore), dillo e fermati su quella fonte. Non ricostruire contenuti a memoria.
- Le operazioni distruttive (spostamenti di massa, merge, cancellazioni, migrazioni di schema) richiedono una conferma esplicita e un commit dedicato.

## Flusso di chiusura

Ogni operazione che scrive termina così, nella radice della wiki:

1. `SB validate <pagine create o modificate>`. In caso di errori, correggi e ripeti, al massimo due volte. Se restano errori, procedi comunque: elenca le pagine problematiche nel riepilogo e nel messaggio di log.
2. `SB index`
3. `SB log "<sintesi in una riga>" --op <skill>`
4. `git add -A && git commit -m "sb(<skill>): <sintesi>"`
5. Se esiste un remote (`git remote` non vuoto): `git push`. Se il push fallisce, non ritentare in loop: segnalalo nel riepilogo, il commit resta locale e `/sb:status` lo mostrerà.

Non lasciare mai la wiki con modifiche non committate.

## Segnali di schema

Quando lo schema non basta, aggiungi una voce in fondo a `schema/proposals.md`, con `n` = numero massimo esistente + 1. Esempi: la stessa struttura ripetuta in un tipo generico, un campo che manca, `unknown-field` ricorrenti.

    - [ ] P<n> · <titolo breve>
      - segnale: <cosa hai osservato, con i link alle pagine>
      - proposta: <modifica allo schema>

Non modificare `schema/types/` fuori da `/sb:schema` o `/sb:init`.
````

`skills/init/SKILL.md`:

````markdown
---
name: init
description: Crea una nuova wiki Second Brain con un'intervista che genera lo schema su misura, partendo dal preset Head of Engineering. Usa quando l'utente vuole creare o inizializzare un second brain o una nuova wiki, o quando un comando sb viene lanciato fuori da una wiki.
argument-hint: "[path]"
---

# /sb:init: crea una wiki

Argomenti: `$ARGUMENTS`. Contiene il percorso opzionale della nuova wiki; il default è la directory corrente.

## 0. Prima di iniziare

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill. Da qui in poi `PRESET` = `BASE/../../presets/head-of-engineering`.
2. Determina la cartella di destinazione `TARGET`.
   - Se `SB version --wiki TARGET` ritorna `wiki` non nullo, è già una wiki: fermati e proponi `/sb:status`.
   - Se `TARGET` contiene file diversi da `.git` e `.DS_Store`, fermati e chiedi un'altra cartella. Non sovrascrivere mai nulla.

## 1. Intervista

Una domanda per messaggio, preferibilmente a scelta multipla, con risposte brevi. Ogni 2–3 risposte riassumi ciò che hai capito. Gli argomenti, in quest'ordine:

1. **Contesto**: azienda o unità, ruolo, perimetro (quanti team, quante persone).
2. **Persone e team**: riporti diretti, team con i loro lead, il tuo manager, i peer chiave. Raccogli nomi e cognomi: diventeranno le prime pagine.
3. **Ritmi**: cadenza dei 1:1, da cui ricavi `one_on_one_gap_days` (cadenza + circa il 50%); meeting ricorrenti importanti; rituali (planning, review, staff meeting).
4. **Sorgenti esterne**: spazi Confluence e progetti Jira rilevanti. Per ciascuno chiedi la chiave, a cosa serve e ogni quanto cambia, da cui ricavi `stale_after_days`. Chiedi anche se usa mail e calendario. Verifica quali tool MCP (Atlassian, Microsoft 365) sono disponibili in questa sessione e dillo.
5. **Cosa vuoi ritrovare**: le 3–5 domande che vorresti poter fare alla wiki. Servono ad adattare tipi, briefing e report.
6. **Tipi**: mostra i tipi del preset per layer, una riga ciascuno, ricavata dai file in `PRESET/types/`. Chiedi cosa rinominare, aggiungere o togliere. `task` e `source-note` sono obbligatori.
7. **Repository**: URL del remote git (o nessuno per ora) e branch (default `main`).

## 2. Proposta di schema

1. Crea una cartella temporanea (`mktemp -d`) e copia il preset: `cp -R "PRESET" "<tmp>/schema"`.
2. Modifica la copia secondo le risposte:
   - `layers.md`: le soglie;
   - `sources.md`: una voce di frontmatter per sorgente (`<id>: {system: …, scope: <CHIAVE>, covers: [tipi], stale_after_days: N}`) e una sezione di prosa per ciascuna;
   - `types/*.md`: rinomina, aggiungi o togli tipi; adatta la prosa al contesto reale (nomi dei team, rituali). Un tipo nuovo segue lo stesso formato degli altri: frontmatter `name`, `layer`, `folder` (= `<layer>/<plurale>`), `fields`, `required`, poi la prosa con **Crea**, **Non creare** e **Struttura del corpo**;
   - `briefings/` e `reports/`: adatta le sezioni alle domande del punto 1.5.
3. Mostra la proposta in modo compatto: tipi per layer, sorgenti, soglie, briefing, report. Chiedi conferma e applica le correzioni finché l'utente non approva.

## 3. Creazione

1. Esegui `SB scaffold "<tmp>/schema" "TARGET"`. Se esce con 2, mostra `error`, correggi lo schema temporaneo e riprova.
2. **Seed**:
   - cattura le risposte dell'intervista utili come fonte in `raw/AAAA/MM/AAAA-MM-GG-init-intervista.md` (`kind: dictation`);
   - crea le pagine `person` e `team` raccolte al punto 1.2, con i soli fatti dichiarati dall'utente e la citazione a quel file.
3. **Git** nella cartella `TARGET`:
   - se manca `.git`: `git init -b <branch>`;
   - se c'è un remote e non esiste `origin`: `git remote add origin <url>`.
4. Chiudi con il flusso standard delle convenzioni (`--op init`). Per il primo push usa `git push -u origin <branch>`.

## 4. Riepilogo

In 5–8 righe:
- dove sta la wiki;
- i tipi creati;
- le pagine seed;
- l'esito del push.

Poi suggerisci i primi passi:
- aprire Claude Code dentro la wiki;
- `/sb:put` per il primo 1:1 o documento;
- `/sb:status`.
````

`skills/status/SKILL.md`:

````markdown
---
name: status
description: Cruscotto della wiki Second Brain con task scaduti e in scadenza, delegati in ritardo, 1:1 trascurati, sorgenti da riallineare, proposte di schema, problemi di lint e stato git. Usa per "com'è messa la wiki?", "cosa ho in sospeso?", "da dove comincio oggi?".
---

# /sb:status: cruscotto

Solo lettura: non scrivere file e non fare commit.

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.
2. Esegui `SB status`. Se esce con 2 perché la cartella non è una wiki, proponi `/sb:init`.
3. Controlla lo stato git:
   - `git status --porcelain` per le modifiche non committate;
   - se esiste un upstream, `git rev-list --count @{u}..HEAD` per i commit non pushati.
4. Mostra al massimo 15 righe. Includi **solo le sezioni non vuote**, in quest'ordine:
   - **Scaduti** (tuoi): titolo · scadenza · priorità
   - **In scadenza** (entro `due_soon_days`): titolo · scadenza
   - **Delegati in ritardo**: titolo · owner · scadenza
   - **1:1 da fare**: persona · giorni dall'ultimo
   - **Sorgenti da riallineare**: titolo · età in giorni, oppure "mai sincronizzata"
   - **Proposte di schema aperte**: numero
   - **Lint**: errori · avvisi
   - **Git**: modifiche non committate · commit non pushati

   Se una sezione ha più di 3 elementi, mostra i primi 3 e "+N".
5. Chiudi con 1–3 azioni suggerite, concrete e legate a ciò che hai mostrato. Esempi: `/sb:prep Luca Bianchi`, `/sb:sync`, `/sb:lint --fix`, `git push`. Se è tutto in ordine, dillo in una riga.
````

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Valida il plugin**

Run: `claude plugin validate .`
Expected: nessun errore. Le skill `init` e `status` compaiono nell'inventario. Se `argument-hint` viene segnalato come campo non riconosciuto, rimuovilo da tutte le skill e annotalo nel commit.

- [ ] **Step 6: Commit**

```bash
git add references skills tests/test_plugin_layout.py
git commit -m "feat(skills): shared conventions, init and status"
```

---

### Task 14: Skill `put` e `sync`

**Files:**
- Create: `skills/put/SKILL.md`, `skills/sync/SKILL.md`

**Interfaces:**
- Consumes: `references/conventions.md`; i comandi `resolve`, `tasks list`, `sources stale`, `validate`, `index`, `log`; il formato raw e source-note della spec (§3.5, §3.6).
- Produces: `/sb:put` (pipeline di ingestione), `/sb:sync` (re-ingest guidato dalla versione, con `--check` come aggancio per le routine del sotto-progetto 2).

- [ ] **Step 1: Verifica che il test di layout copra le nuove skill**

Run: `python3 -m unittest discover -s tests -p 'test_plugin_layout.py' -v`
Expected: PASS. `test_skills_are_well_formed` controlla ogni `skills/*/SKILL.md`, quindi le nuove skill verranno controllate allo Step 3.

- [ ] **Step 2: Scrivi le skill**

`skills/put/SKILL.md`:

````markdown
---
name: put
description: Fa entrare contenuti nella wiki Second Brain (note e dettati di 1:1 e riunioni, file locali come PDF e trascrizioni, pagine Confluence, ticket o query Jira, thread mail, link web), estraendo persone, decisioni, task e rischi e aggiornando le pagine giuste. Usa quando l'utente racconta qualcosa da ricordare ("ho fatto l'1:1 con…", "abbiamo deciso che…"), incolla note o chiede di importare, ingerire o salvare un contenuto.
argument-hint: "<testo | file | url | confluence:… | jira:… | mail:…> [--as <tipo>] [--plan]"
---

# /sb:put: fa entrare contenuti

Argomenti: `$ARGUMENTS`

## 0. Prima di iniziare

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.
2. Leggi `schema/layers.md` e `schema/sources.md`, ed elenca i tipi disponibili con `ls schema/types`.
3. Opzioni:
   - `--as <tipo>` fissa il tipo principale, che deve esistere in `schema/types`;
   - `--plan` obbliga a mostrare il piano prima di scrivere.
4. Se non c'è input, chiedi: "Cosa vuoi mettere nella wiki?".

## 1. Classifica l'input

| Input | Come riconoscerlo | Cattura |
|---|---|---|
| Testo libero | qualsiasi testo che non sia un riferimento | `raw/`, `kind: dictation` (`transcript` se è una trascrizione) |
| File o cartella | il percorso esiste | `raw/`, `kind: file`. Una cartella è un lotto, da trattare un file alla volta |
| Confluence | URL `…atlassian.net/wiki/…` oppure `confluence:<SPAZIO>/<id>` | source-note |
| Jira | `jira:<KEY>`, oppure `"jira: <JQL>"` (lotto) | source-note, una per ticket |
| Mail | `mail: <criterio di ricerca>` | source-note, una per thread |
| Web | URL http(s) | source-note |

Per le sorgenti esterne usa i tool MCP disponibili in sessione:
- Atlassian per pagine Confluence, issue Jira e ricerche JQL;
- Microsoft 365 per la mail;
- WebFetch per il web.

Se il tool necessario manca o fallisce, dillo e fermati per quella sorgente.

## 2. Cattura

**Grezzo.** Scrivi `raw/AAAA/MM/AAAA-MM-GG-<slug>.md`, con slug in minuscolo, a trattini e descrittivo:

    ---
    kind: dictation
    captured: 2026-10-02
    origin: chat
    ---
    <contenuto originale, intatto>

`origin` vale `chat` per il testo incollato o dettato, oppure il percorso del file originale. Per un file binario (PDF, DOCX…):
- copia il file accanto al `.md`, con lo stesso slug e l'estensione originale;
- metti nel `.md` il testo estratto. Per i PDF usa Read.

**Source-note** in `knowledge/sources/`:
- titolo `<Sistema> · <titolo del documento>`, senza i caratteri vietati;
- `external`: `confluence:<SPAZIO>/<pageId>`, `jira:<KEY>`, `mail:<id del thread>` oppure `url:<url>`;
- `version`: versione della pagina Confluence, `updated` del ticket Jira, data dell'ultimo messaggio;
- `synced`: oggi;
- corpo come da prosa del tipo `source-note`.

Se esiste già una source-note con lo stesso `external`, aggiornala seguendo le regole di `/sb:sync`, passo 3.

Se il sistema o lo scope (`confluence`, `jira`) non è registrato in `schema/sources.md`, chiedi se registrarlo. In caso affermativo aggiungi la voce `<id>: {system, scope, covers, stale_after_days}` e una riga di prosa. `url` e `mail` non si registrano.

## 3. Analisi

1. **Entità**: per ogni persona, team, progetto, sistema o fornitore menzionato esegui `SB resolve "<nome>"`, con `--type` se il tipo è chiaro. Applica le regole di ambiguità delle convenzioni.
2. **Estrai** ciò che conta per il management:
   - **fatti stabili** per il layer knowledge (ruoli, responsabilità, architetture, processi);
   - **eventi** per il layer operations: l'incontro stesso (`one-on-one`, `meeting`), le **decisioni**, i **rischi**, gli **obiettivi**;
   - **task**: impegni dell'utente ("devo…", "mi prendo…") e impegni altrui verso l'utente ("Luca mi manda…", "ho chiesto ad Anna di…");
   - **opinioni dell'utente**: valutazioni, preoccupazioni, giudizi. Vanno nella sezione `## Note` della pagina pertinente.
3. **Tipo principale**: fissato da `--as`, altrimenti dedotto. Un dettato su un incontro a due è un `one-on-one`.

## 4. Piano

Prepara l'elenco delle modifiche: pagina · crea o aggiorna · cosa cambia, in una riga.

**Mostralo e attendi conferma** se c'è `--plan` o se si verifica uno di questi casi:
- un'entità nuova somiglia a una esistente;
- il tipo è incerto;
- c'è un contrasto con una sorgente esterna;
- verrebbero toccate più di 15 pagine.

Altrimenti procedi.

## 5. Scrittura

Per ogni pagina rileggi la prosa del suo tipo in `schema/types/<tipo>.md` e seguila.

- **Knowledge (consolida)**: integra nella sezione giusta. Se una frase è superata, riscrivila invece di accodarne una nuova. Aggiorna `updated`. La cronologia sta nelle pagine operations.
- **Operations (crea)**: una pagina per evento o item, con titolo datato dove il tipo lo prevede (`2026-10-02 1on1 Luca Bianchi`).
- **Propagazione**: se un'informazione operativa cambia la conoscenza stabile, aggiorna anche la pagina knowledge e collega le due pagine.
- **Task**: segui le regole dei campi nella prosa del tipo `task`. Prima di crearne uno, controlla con `SB tasks list --view all --person "<persona>"` (o `--project`) che non esista già. Se esiste, aggiornalo e aggiungi la riga datata.
- **Citazioni**: ogni fatto rilevante porta `^[<fonte>]`. Aggiungi la fonte a `sources` di ogni pagina toccata.

## 6. Chiusura

Esegui il flusso standard delle convenzioni con `--op put`. Il messaggio è una sintesi, per esempio "1:1 Luca Bianchi: 2 task, 1 rischio".

Nei lotti (cartella, JQL, più riferimenti) esegui i passi 2–5 per ogni elemento e **un solo** passo 6 alla fine.

## 7. Riepilogo per l'utente (3–6 righe)

- **Creato**: pagine nuove, come wikilink.
- **Aggiornato**: pagine modificate.
- **Task**: titolo · owner · scadenza.
- **Dubbi**: cosa non hai potuto inferire o richiede una sua decisione.
- **Segnali di schema** registrati, se ce ne sono.
````

`skills/sync/SKILL.md`:

````markdown
---
name: sync
description: Riallinea la wiki Second Brain con le sorgenti esterne (Confluence, Jira e simili) trovando le source-note stantie o cambiate e rielaborando solo ciò che è cambiato. Usa per "aggiorna da Confluence", "riallinea le sorgenti", "cosa è cambiato nelle fonti?".
argument-hint: "[<source-id> | <pagina> | --all] [--check]"
---

# /sb:sync: riallinea le sorgenti esterne

Argomenti: `$ARGUMENTS`

## 0. Prima di iniziare

Leggi `BASE/../../references/conventions.md` (BASE è la base directory di questa skill) e `schema/sources.md`.

## 1. Candidati

1. Esegui `SB sources stale` per trovare le source-note oltre la soglia o mai sincronizzate.
2. Scegli l'insieme da verificare in base all'argomento:
   - `<source-id>`: tutte le source-note il cui `external` appartiene a quella sorgente (stesso sistema e scope; cercale con `grep -rl 'external: "<system>:<SCOPE>' knowledge/sources`);
   - `<pagina>`: `SB resolve "<pagina>" --type source-note`;
   - `--all` o nessun argomento: le stantie del punto 1.
3. Per ogni candidata leggi via MCP la versione attuale (versione della pagina Confluence, `updated` del ticket Jira) e confrontala con `version`. Classifica ciascuna come:
   - **cambiata**: la versione è diversa;
   - **invariata**: la versione è la stessa;
   - **irraggiungibile**: errore o tool mancante.

## 2. Report

Mostra una tabella: titolo · sistema · età · esito. Poi:
- con `--check`: fermati qui, senza scritture e senza commit;
- senza argomenti: chiedi quali delle cambiate rielaborare (default: tutte);
- con `<source-id>`, `<pagina>` o `--all`: procedi con tutte le cambiate.

## 3. Rielaborazione, per ogni source-note scelta

1. **Invariata**: aggiorna solo `synced` alla data di oggi.
2. **Cambiata**: leggi il contenuto attuale e individua cosa è cambiato rispetto alla sintesi. Aggiorna la source-note: sintesi, `version`, `synced`, `updated`.
3. Propaga **solo i fatti cambiati** nelle pagine che citano quella sorgente (`grep -rl "<external>" knowledge operations`):
   - un fatto derivato da questa sorgente si aggiorna e la citazione resta;
   - se il fatto nuovo contrasta con un contenuto che **non** deriva da questa sorgente (una nota dell'utente o un'altra fonte), non sovrascriverlo. Aggiungi accanto `> ⚠️ In contrasto con ^[<external>] (sync del AAAA-MM-GG): <fatto nuovo>` e riportalo nel riepilogo;
   - le sezioni `## Note` non si toccano mai.
4. Le source-note con `authority: migrated` si saltano sempre.
5. Le pagine nuove comparse nello spazio esterno non sono compito di sync: per ingerirle si usa `/sb:put`.

## 4. Chiusura

Esegui il flusso standard con `--op sync`. Messaggio: "N sorgenti riallineate, M pagine aggiornate, K conflitti".

Nel riepilogo elenca le cambiate, le invariate, le irraggiungibili e i conflitti da guardare.
````

- [ ] **Step 3: Esegui i test**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`. `test_skills_are_well_formed` ora controlla anche `put` e `sync`.

- [ ] **Step 4: Valida il plugin**

Run: `claude plugin validate .`
Expected: nessun errore

- [ ] **Step 5: Commit**

```bash
git add skills/put skills/sync
git commit -m "feat(skills): put and sync"
```

---

### Task 15: Skill `ask`, `prep`, `report`, `tasks`

**Files:**
- Create: `skills/ask/SKILL.md`, `skills/prep/SKILL.md`, `skills/report/SKILL.md`, `skills/tasks/SKILL.md`

**Interfaces:**
- Consumes: `references/conventions.md`; i comandi `resolve`, `tasks list`, `sources stale`, `index`, `migrate`; i tipi predefiniti `briefing` (`about`, `for`) e `report` (`kind`, `scope`, `period`); i template `schema/briefings/*` e `schema/reports/*` (Task 12).
- Produces: `/sb:ask`, `/sb:prep`, `/sb:report`, `/sb:tasks`.

- [ ] **Step 1: Scrivi le skill**

`skills/ask/SKILL.md`:

````markdown
---
name: ask
description: Risponde a domande puntuali usando la wiki Second Brain, con citazioni a pagine e fonti, e va sulle sorgenti live (Confluence, Jira) solo se serve. Usa per domande come "cosa abbiamo deciso su X?", "quando ho parlato con Y di Z?", "chi segue W?".
argument-hint: "<domanda> [--live]"
---

# /sb:ask: domanda puntuale

Domanda: `$ARGUMENTS`

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.
2. **Orientati**: leggi `index.md` ed esegui `SB resolve "<nome>"` per ogni entità della domanda.
3. **Cerca**, dal più specifico al più ampio:
   1. le pagine delle entità risolte e i loro backlink (`.sb/backlinks.json`; se manca, esegui `SB index`);
   2. `grep -ril "<parole chiave>" knowledge operations outputs`;
   3. per le domande sul "quando", le pagine operations ordinate per data (titolo datato o campo `date`).
4. **Fonte live**: interroga Confluence o Jira via MCP solo se c'è `--live`, oppure se la wiki non basta e una source-note o `schema/sources.md` indicano dove sta il dettaglio. Se la fonte non è raggiungibile, dillo.
5. **Rispondi**:
   - prima la risposta diretta, in 1–5 frasi;
   - poi le evidenze, ognuna con `[[Pagina]]` e la fonte originale se la pagina la cita (`^[…]`);
   - tieni distinti i fatti dalle opinioni dell'utente (sezioni `## Note`);
   - se la wiki non contiene la risposta, dillo chiaramente e suggerisci cosa ingerire (`/sb:put …`).
6. **Non archiviare.** Se l'utente chiede di salvare la risposta ("salvala" o simile):
   - crea `outputs/reports/Report AAAA-MM-GG risposta <argomento breve>.md` con `type: report`, `kind: answer`, `scope: <argomento>`, `created`;
   - nel corpo metti domanda, risposta ed evidenze;
   - esegui il flusso standard con `--op ask`.
````

`skills/prep/SKILL.md`:

````markdown
---
name: prep
description: Prepara e archivia un briefing per un 1:1, una riunione, una persona o un progetto partendo dalla wiki Second Brain. Usa per "preparami l'1:1 con Luca", "cosa devo sapere per la riunione di domani con il team X?", "fammi il punto sul progetto Y".
argument-hint: "<persona | meeting | progetto | team> [--for <data>]"
---

# /sb:prep: briefing

Argomenti: `$ARGUMENTS`

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.
2. **Target**: esegui `SB resolve "<target>"`; se è ambiguo, chiedi. `--for` accetta una data o un'espressione ("domani", "lunedì") da convertire in data assoluta; il default è oggi.
3. **Template**: scegli in `schema/briefings/` in base al tipo del target. Nel preset:

   | Target | Template |
   |---|---|
   | persona con pagine `one-on-one` | `one-on-one.md` |
   | meeting o serie ricorrente | `meeting.md` |
   | persona senza 1:1 | `person.md` |
   | progetto o team | `project.md` |

   Se nessun template è adatto, usa la struttura di `project.md`. Leggi il template e seguine sezioni e finestra temporale.
4. **Raccogli**:
   - la pagina del target e i suoi backlink (`.sb/backlinks.json`);
   - i task: `SB tasks list --view all --person "<target>"` per una persona, `--project "<target>"` per un progetto. Tieni quelli aperti e quelli chiusi nella finestra;
   - le pagine operations collegate (1:1, meeting, decisioni, rischi, obiettivi), dalla più recente;
   - le source-note collegate, segnalando quelle stantie secondo `SB sources stale`;
   - l'ultimo briefing sullo stesso target in `outputs/briefings/`, per dire cosa è cambiato da allora.
5. **Scrivi** `outputs/briefings/Briefing AAAA-MM-GG <Titolo del target>.md`, con la data di `--for`. Se il file esiste già, aggiornalo.

        ---
        type: briefing
        title: Briefing 2026-10-03 Luca Bianchi
        about: "[[Luca Bianchi]]"
        for: 2026-10-03
        created: 2026-10-02
        ---
        <sezioni del template; ogni punto con il [[link]] alla pagina da cui viene>

6. Mostra in chat il briefing completo, non un riassunto. Poi esegui il flusso standard con `--op prep`.
````

`skills/report/SKILL.md`:

````markdown
---
name: report
description: Produce e archivia sintesi trasversali dalla wiki Second Brain (settimana, mese, rischi, carico del team, update per il proprio manager, cose delegate). Usa per "riepilogo della settimana", "quali rischi abbiamo?", "come sta il carico del team?", "preparami l'update per il mio capo".
argument-hint: "<tipo> [--scope <entità>] [--period <periodo>]"
---

# /sb:report: sintesi trasversale

Argomenti: `$ARGUMENTS`

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.
2. **Tipo**: corrisponde a un file in `schema/reports/` (`ls schema/reports`). Se il tipo manca o non esiste, mostra quelli disponibili con il loro titolo e chiedi.
3. **Periodo e scope**:
   - `--period` accetta `AAAA-MM`, `AAAA-Www`, `AAAA-MM-GG..AAAA-MM-GG` o espressioni ("settimana scorsa"). Il default è nel template;
   - `--scope` va risolto con `SB resolve`. Senza scope il report copre tutta la wiki.
4. **Raccogli** secondo il template:
   - le righe di `log.md` nel periodo, per sapere cosa è entrato;
   - le pagine create o aggiornate nel periodo (`created`, `updated` o data nel titolo);
   - i task con la vista adatta (`SB tasks list --view all|delegated|overdue`);
   - rischi, decisioni e obiettivi pertinenti allo scope.
5. **Scrivi** `outputs/reports/Report AAAA-MM-GG <tipo>[ <scope>].md`:
   - frontmatter: `type: report`, `title`, `kind: <tipo>`, `scope` (se presente), `period`, `created`;
   - corpo secondo il template, con ogni affermazione collegata alla pagina d'origine.
6. Mostra in chat il report completo. Poi esegui il flusso standard con `--op report`.
````

`skills/tasks/SKILL.md`:

````markdown
---
name: tasks
description: Mostra e gestisce i task della wiki Second Brain (tuoi, delegati, scaduti, di oggi o della settimana) e permette di crearli, chiuderli, abbandonarli o aggiornarli. Usa per "cosa devo fare oggi?", "cosa aspetto dagli altri?", "chiudi il task…", "sposta la scadenza di…", "aggiungi un task…".
argument-hint: "[mine|delegated|overdue|today|week|blocked|all] [--project X] [--person Y] [--priority P] | add <testo> | done <task> | drop <task> | update <task> <modifica>"
---

# /sb:tasks: vedere e gestire i task

Argomenti: `$ARGUMENTS`

Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.

## Viste (solo lettura)

Si applicano quando il primo argomento è una vista, un filtro, oppure manca (default `mine`). In linguaggio naturale: "oggi" → `today`, "questa settimana" → `week`, "cosa aspetto dagli altri" → `delegated`.

1. `SB tasks list --view <vista> [--project …] [--person …] [--priority …]`
2. Mostra una tabella compatta nell'ordine restituito: `#` · titolo · stato · owner (solo se delegato) · scadenza (⚠️ se `overdue`) · priorità. Oltre le 20 righe, mostra le prime 20 e il totale.
3. Riga finale: aperti · scaduti · delegati. Se utile, suggerisci un'altra vista.

Nessun commit.

## Azioni

- **`add <testo>`**: crea un task con le regole della prosa del tipo `task` e della skill put (passo 5).
  - Se il testo contiene contesto oltre al titolo, catturalo in `raw/` (`kind: dictation`) e citalo.
  - Altrimenti lascia `sources` vuoto.
- **`done <task>` / `drop <task>`**:
  1. Risolvi con `SB resolve "<task>" --type task`; se è ambiguo, mostra i candidati e chiedi.
  2. Imposta `status: done` o `dropped` e aggiorna `updated`.
  3. Accoda al corpo `- AAAA-MM-GG: chiuso`, oppure `- AAAA-MM-GG: abbandonato: <motivo>` se l'utente lo indica.
- **`update <task> <modifica>`**:
  1. Risolvi come sopra.
  2. Applica la modifica descritta in linguaggio naturale: scadenza, priorità, owner, stato (`blocked` con il motivo nel corpo), titolo. Per cambiare titolo usa un'operazione `retitle` con `SB migrate`, così i link restano validi.
  3. Accoda `- AAAA-MM-GG: <cosa è cambiato>`.

Dopo ogni azione esegui il flusso standard con `--op tasks` e conferma in una riga cosa è cambiato.
````

- [ ] **Step 2: Esegui i test**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 3: Valida il plugin**

Run: `claude plugin validate .`
Expected: nessun errore

- [ ] **Step 4: Commit**

```bash
git add skills/ask skills/prep skills/report skills/tasks
git commit -m "feat(skills): ask, prep, report and tasks"
```

---

### Task 16: Skill `lint` e `schema` + copertura completa dei comandi

**Files:**
- Create: `skills/lint/SKILL.md`, `skills/schema/SKILL.md`
- Modify: `tests/test_plugin_layout.py` (test sull'insieme completo dei comandi)

**Interfaces:**
- Consumes: `references/conventions.md`; i comandi `lint`, `resolve`, `migrate`, `validate`; il formato di `schema/proposals.md` e del piano di migrazione (Task 10).
- Produces: `/sb:lint`, `/sb:schema`. L'insieme delle skill diventa esattamente `{init, status, put, sync, ask, prep, report, tasks, lint, schema}`.

- [ ] **Step 1: Scrivi il test che fallisce**

Aggiungi a `SkillsTest` in `tests/test_plugin_layout.py`:

```python
    def test_all_commands_present(self):
        names = {p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")}
        self.assertEqual(names, {"init", "status", "put", "sync", "ask", "prep", "report", "tasks", "lint", "schema"})
```

- [ ] **Step 2: Esegui il test e verifica che fallisca**

Run: `python3 -m unittest discover -s tests -p 'test_plugin_layout.py' -v`
Expected: FAIL su `test_all_commands_present`: mancano `lint` e `schema`.

- [ ] **Step 3: Scrivi le skill**

`skills/lint/SKILL.md`:

````markdown
---
name: lint
description: Manutenzione della wiki Second Brain che cerca link rotti, pagine orfane, campi non validi, sorgenti stantie, task scaduti, item fermi, duplicati, contraddizioni e pagine da consolidare, e corregge con --fix. Usa per "fai pulizia nella wiki", "controlla la wiki", "ci sono problemi nella wiki?".
argument-hint: "[--fix] [--only structural|semantic]"
---

# /sb:lint: manutenzione

Argomenti: `$ARGUMENTS`

Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill. Senza `--fix` la skill è **solo lettura**: non scrive file e non fa commit.

## 1. Controlli strutturali

Salta se c'è `--only semantic`.

Esegui `SB lint`. Raggruppa le issue per codice e mostra per ciascun gruppo il conteggio e fino a 5 pagine.

## 2. Controlli semantici

Salta se c'è `--only structural`.

Parti da `index.md` e dalle pagine aggiornate di recente, e cerca:
- **duplicati probabili**: pagine dello stesso tipo con titoli simili (`SB resolve "<titolo>" --type <tipo>` con altri candidati sopra 0.5) o con contenuti sovrapposti;
- **contraddizioni**: fatti incompatibili tra pagine (ruoli, date, responsabili, stato di un progetto);
- **fatti superati**: pagine che citano una source-note con `synced` più recente dell'`updated` della pagina;
- **pagine da consolidare**: pagine knowledge con cronologie accodate invece di sezioni stabili, o più lunghe di circa 150 righe;
- **segnali di schema**: `unknown-field` ricorrenti, tipi generici usati sempre con la stessa struttura, campi che mancano.

Per ogni rilievo mostra le pagine coinvolte e la correzione proposta.

## 3. Correzioni

Solo con `--fix`.

1. **Meccaniche**: applicale subito, tutte in un unico commit.
   - `alias-link`: riscrivi `[[alias]]` come `[[Titolo|alias]]`.
   - `filename-mismatch` e `wrong-folder`: operazione `move` verso `<folder del tipo>/<title>.md` con `SB migrate`.
   - Date non ISO convertibili senza ambiguità.

   Poi esegui il flusso standard con `--op lint`.
2. **Semantiche**: una alla volta. Proponi la correzione e attendi un sì esplicito.
   - Unire due duplicati è un'operazione distruttiva. Fondi i contenuti nella pagina che resta, poi usa `retitle` o `move` con `SB migrate` per riallineare i link, ed elimina la pagina assorbita con `git rm`. Fai un commit dedicato.
   - Una contraddizione si risolve con le regole delle sorgenti: sui fatti vince la fonte esterna, le note dell'utente non si toccano.
3. **Segnali di schema**: registrali in `schema/proposals.md` nel formato delle convenzioni e indica `/sb:schema proposals`.

## 4. Riepilogo

Riporta i conteggi prima e dopo, le correzioni applicate e i rilievi rimasti aperti.
````

`skills/schema/SKILL.md`:

````markdown
---
name: schema
description: Mostra e fa evolvere lo schema della wiki Second Brain (elenca i tipi, presenta le proposte raccolte, aggiunge o modifica tipi e campi, applica migrazioni sulle pagine esistenti). Usa per "aggiungi un tipo vendor", "lo schema va cambiato", "che proposte di schema ci sono?".
argument-hint: "[proposals | add <tipo> | change <tipo> <modifica> | apply <id>]"
---

# /sb:schema: evoluzione dello schema

Argomenti: `$ARGUMENTS`

Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.

Lo schema sta in `schema/`. I tipi `task` e `source-note` non si eliminano e non perdono i campi da cui dipende il toolkit:
- `task`: `status` (con `closed`), `owner`, `due`, `priority`, `related`;
- `source-note`: i campi comuni `external`, `version`, `synced`.

## Senza argomenti (solo lettura)

1. Per ogni layer elenca i tipi, con il numero di pagine (da `index.md`) e i campi principali.
2. Riporta il numero di proposte aperte, cioè le righe `- [ ]` in `schema/proposals.md`.

## `proposals`

Per ogni proposta aperta mostra:
1. il segnale osservato e le pagine coinvolte;
2. il **diff dello schema**: quali file di `schema/types/` cambiano e come;
3. il **piano di migrazione** sulle pagine (spostamenti, retitle, rinomina di campi, nuovi valori) con il numero di pagine toccate.

Per ciascuna chiedi se applicarla (`apply`), scartarla (segna `- [-]` e aggiungi il motivo) o rimandarla.

## `add <tipo>` / `change <tipo> <modifica>`

Raccogli ciò che manca, una domanda alla volta:
- layer;
- cartella (`<layer>/<plurale>`);
- campi (`kind`, `values`, `closed` per gli status, `to` per i link);
- campi obbligatori;
- prosa con **Crea**, **Non creare** e **Struttura del corpo**.

Registra il tutto come nuova proposta in `schema/proposals.md` e prosegui come `apply` su quella proposta.

## `apply <id>`

1. Mostra di nuovo il diff e il piano di migrazione, poi chiedi una conferma esplicita: è un'operazione distruttiva.
2. Modifica o crea i file in `schema/types/`.
3. Scrivi il piano in un file temporaneo (`mktemp`) nel formato del toolkit:

        {"ops": [
          {"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/vendors/Acme.md", "set": {"type": "vendor"}},
          {"op": "retitle", "path": "knowledge/people/Luca.md", "title": "Luca Bianchi"},
          {"op": "rename_field", "type": "person", "from": "role", "to": "position"},
          {"op": "set", "path": "operations/tasks/X.md", "fields": {"priority": "high", "owner": null}}
        ]}

   Se la proposta tocca solo lo schema e nessuna pagina, salta questo passo e il successivo.
4. Esegui `SB migrate <piano> --dry-run` e mostra le modifiche. Poi `SB migrate <piano>`.
5. Esegui `SB validate`. In caso di errori, correggi le pagine (per esempio valori da rimappare su un nuovo enum) e ripeti.
6. Segna la proposta `- [x]` in `schema/proposals.md`, con la data.
7. Esegui il flusso standard con `--op schema`, in un commit dedicato `sb(schema): P<n> <titolo>`.
````

- [ ] **Step 4: Esegui i test e verifica che passino**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 5: Valida il plugin con controllo stretto**

Run: `claude plugin validate . --strict`
Expected: exit 0. Se compaiono avvisi su campi non riconosciuti (per esempio `argument-hint`), rimuovi il campo da tutte le skill, riesegui i test e il validate, e annota la modifica nel commit.

- [ ] **Step 6: Commit**

```bash
git add skills/lint skills/schema tests/test_plugin_layout.py
git commit -m "feat(skills): lint and schema; complete command set"
```

---

### Task 17: Wiki di esempio, scenari di accettazione, README

**Files:**
- Create: `tests/fixtures/sample-wiki/` (generata con `scaffold`, più le pagine elencate sotto)
- Create: `tests/test_fixtures.py`, `tests/scenarios/setup.sh`, `tests/scenarios/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: CLI `scaffold`, `index`, `validate`; il preset; tutte le skill.
- Produces: una wiki di esempio valida (0 issue in `validate`) e scenari manuali ripetibili per le skill.

- [ ] **Step 1: Scrivi il test che fallisce**

`tests/test_fixtures.py`:

```python
import unittest

from helpers import ROOT
from sb_core.validate import validate
from sb_core.wiki import Wiki

FIXTURE = ROOT / "tests" / "fixtures" / "sample-wiki"


class SampleWikiTest(unittest.TestCase):
    def test_sample_wiki_is_valid(self):
        wiki = Wiki(FIXTURE)
        self.assertEqual([i.to_dict() for i in validate(wiki)], [])
        self.assertGreaterEqual(len(wiki.pages()), 8)
        self.assertIn("conf-eng", wiki.sources)


if __name__ == "__main__":
    unittest.main()
```

Run: `python3 -m unittest discover -s tests -p 'test_fixtures.py' -v`
Expected: ERROR `WikiError: … non è dentro una wiki second-brain`

- [ ] **Step 2: Genera la wiki di esempio**

Run: `python3 toolkit/sb.py scaffold presets/head-of-engineering tests/fixtures/sample-wiki`
Expected: exit 0, JSON con `"path"`.

Poi sostituisci il frontmatter di `tests/fixtures/sample-wiki/schema/sources.md` (il corpo resta invariato):

```markdown
---
sources:
  conf-eng: {system: confluence, scope: ENG, covers: [process, system], stale_after_days: 30}
---
```

Crea questi file:

`tests/fixtures/sample-wiki/raw/2026/09/2026-09-15-1on1-luca.md`:

```markdown
---
kind: dictation
captured: 2026-09-15
origin: chat
---
1:1 con Luca. Il team Platform sta pianificando la migrazione del DB. Luca mi manda la stima entro il 9 ottobre.
Io devo preparare il budget Q4 con Anna entro metà ottobre, è urgente.
```

`tests/fixtures/sample-wiki/knowledge/people/Luca Bianchi.md`:

```markdown
---
type: person
title: Luca Bianchi
aliases: [Luca]
role: Engineering Manager
relationship: report
team: "[[Platform]]"
created: 2026-09-15
updated: 2026-09-15
sources: [raw/2026/09/2026-09-15-1on1-luca]
---
## Ruolo e contesto
Engineering Manager del team [[Platform]]. ^[raw/2026/09/2026-09-15-1on1-luca]

## Obiettivi e crescita

## Temi aperti
- Stima della [[Migrazione DB]], vedi [[2026-09-15 1on1 Luca Bianchi]].

## Note
```

`tests/fixtures/sample-wiki/knowledge/people/Anna Neri.md`:

```markdown
---
type: person
title: Anna Neri
role: Finance Business Partner
relationship: stakeholder
created: 2026-09-15
sources: [raw/2026/09/2026-09-15-1on1-luca]
---
## Ruolo e contesto
Referente finance per il budget di engineering. ^[raw/2026/09/2026-09-15-1on1-luca]

## Note
```

`tests/fixtures/sample-wiki/knowledge/teams/Platform.md`:

```markdown
---
type: team
title: Platform
lead: "[[Luca Bianchi]]"
status: active
created: 2026-09-15
sources: [raw/2026/09/2026-09-15-1on1-luca]
---
## Missione e perimetro
Piattaforma dati e infrastruttura condivisa; segue la [[Migrazione DB]]. ^[raw/2026/09/2026-09-15-1on1-luca]

## Persone
- [[Luca Bianchi]]: lead.
```

`tests/fixtures/sample-wiki/knowledge/projects/Migrazione DB.md`:

```markdown
---
type: project
title: Migrazione DB
status: active
owner: "[[Luca Bianchi]]"
team: "[[Platform]]"
created: 2026-09-15
sources: [raw/2026/09/2026-09-15-1on1-luca]
---
## Obiettivo
Migrare il database principale sulla nuova piattaforma. ^[raw/2026/09/2026-09-15-1on1-luca]

## Stato
In pianificazione; stima attesa da [[Luca Bianchi]].
```

`tests/fixtures/sample-wiki/knowledge/sources/Confluence · Incident Management.md`:

```markdown
---
type: source-note
title: Confluence · Incident Management
external: "confluence:ENG/123456789"
version: 7
synced: 2026-08-01
created: 2026-08-01
---
## Sintesi
Processo di gestione degli incidenti del team [[Platform]]: severità, on-call, post-mortem.

## Pagine collegate
- [[Platform]]
```

`tests/fixtures/sample-wiki/operations/one-on-ones/2026-09-15 1on1 Luca Bianchi.md`:

```markdown
---
type: one-on-one
title: 2026-09-15 1on1 Luca Bianchi
with: "[[Luca Bianchi]]"
date: 2026-09-15
created: 2026-09-15
sources: [raw/2026/09/2026-09-15-1on1-luca]
---
## Temi
- Pianificazione della [[Migrazione DB]]. ^[raw/2026/09/2026-09-15-1on1-luca]

## Impegni
- [[Ricevere da Luca la stima della migrazione DB]]
- [[Preparare il budget Q4]]
```

`tests/fixtures/sample-wiki/operations/tasks/Ricevere da Luca la stima della migrazione DB.md`:

```markdown
---
type: task
title: Ricevere da Luca la stima della migrazione DB
status: todo
owner: "[[Luca Bianchi]]"
due: 2026-10-09
related: ["[[Migrazione DB]]", "[[2026-09-15 1on1 Luca Bianchi]]"]
created: 2026-09-15
sources: [raw/2026/09/2026-09-15-1on1-luca]
---
Luca manda la stima della migrazione entro il 9 ottobre. ^[raw/2026/09/2026-09-15-1on1-luca]
```

`tests/fixtures/sample-wiki/operations/tasks/Preparare il budget Q4.md`:

```markdown
---
type: task
title: Preparare il budget Q4
status: todo
due: 2026-10-15
priority: high
related: ["[[Anna Neri]]", "[[2026-09-15 1on1 Luca Bianchi]]"]
created: 2026-09-15
sources: [raw/2026/09/2026-09-15-1on1-luca]
---
Budget Q4 da preparare con Anna, urgente. ^[raw/2026/09/2026-09-15-1on1-luca]
```

Poi:

Run: `python3 toolkit/sb.py index --wiki tests/fixtures/sample-wiki && python3 toolkit/sb.py validate --wiki tests/fixtures/sample-wiki`
Expected: `index` exit 0 con `"pages": 8`; `validate` exit 0 con `"issues": []`.

- [ ] **Step 3: Esegui il test e verifica che passi**

Run: `python3 -m unittest discover -s tests -v`
Expected: tutti `ok`

- [ ] **Step 4: Script e scenari di accettazione**

`tests/scenarios/setup.sh`:

```bash
#!/usr/bin/env bash
# Crea una copia usa-e-getta della wiki di esempio, in un repo git locale,
# e stampa il comando per aprirla con il plugin di questo repo.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WIKI="$(mktemp -d)/sample-wiki"
cp -R "$REPO/tests/fixtures/sample-wiki" "$WIKI"
cd "$WIKI"
git init -q -b main
git add -A
git commit -q -m "fixture"
echo "WIKI=$WIKI"
echo "REPO=$REPO"
echo "Apri con:  cd \"$WIKI\" && claude --plugin-dir \"$REPO\""
```

Poi: `chmod +x tests/scenarios/setup.sh`

`tests/scenarios/README.md`:

````markdown
# Scenari di accettazione delle skill

Le skill sono istruzioni per Claude: si verificano eseguendole su una wiki di prova e controllando il risultato con il toolkit. Ogni scenario parte da una copia pulita:

```bash
eval "$(tests/scenarios/setup.sh | grep -E '^(WIKI|REPO)=')"
cd "$WIKI" && claude --plugin-dir "$REPO"
```

In un secondo terminale, nella stessa cartella `$WIKI`, esegui le verifiche. `SB` sta per `python3 "$REPO/toolkit/sb.py"`.

## S1 · `/sb:put` di un 1:1 (estrazione, deduplica dei task, citazioni)

Comando:

    /sb:put --as one-on-one 1:1 con Luca oggi. Vuole crescere verso staff engineer entro un anno. È preoccupato per i turni di on-call del team Platform. Conferma che mi manda la stima della migrazione DB entro venerdì. Io devo parlare con Anna del budget per l'on-call.

Verifiche:
- `SB validate` → exit 0.
- `ls operations/one-on-ones/` → c'è un nuovo `<oggi> 1on1 Luca Bianchi.md` con `with: "[[Luca Bianchi]]"`.
- `SB tasks list --view all --person "Luca Bianchi"` → **un solo** task sulla stima della migrazione (quello esistente, aggiornato), con `due` = il prossimo venerdì.
- `SB tasks list --view mine` → c'è un task nuovo sul budget per l'on-call, senza owner, con `[[Anna Neri]]` in `related`.
- `ls raw/$(date +%Y/%m)/` → c'è il dettato catturato.
- `knowledge/people/Luca Bianchi.md` → l'aspirazione a staff engineer è in "Obiettivi e crescita", con `^[raw/…]`.
- `git log -1 --format=%s` → inizia con `sb(put):`, e `git status --porcelain` è vuoto.

## S2 · `/sb:ask` (risposta citata, nessuna scrittura)

Comando: `/sb:ask chi guida il team Platform e su cosa sta lavorando?`

Verifiche:
- la risposta cita `[[Luca Bianchi]]`, `[[Platform]]` e `[[Migrazione DB]]`;
- `git status --porcelain` è vuoto e `git log -1 --format=%s` è ancora `fixture`.

## S3 · `/sb:prep` (briefing archiviato)

Comando: `/sb:prep Luca Bianchi`

Verifiche:
- esiste `outputs/briefings/Briefing <oggi> Luca Bianchi.md` con `type: briefing` e `about: "[[Luca Bianchi]]"`;
- il briefing contiene il task sulla stima e le sezioni del template `one-on-one`;
- `SB validate` → exit 0; `git log -1 --format=%s` inizia con `sb(prep):`.

## S4 · `/sb:tasks` (vista in sola lettura, poi chiusura)

Comandi: `/sb:tasks`, poi `/sb:tasks done budget Q4`

Verifiche:
- dopo il primo comando, `git status --porcelain` è vuoto;
- dopo il secondo, `operations/tasks/Preparare il budget Q4.md` ha `status: done` e una riga `- <oggi>: chiuso`;
- `SB tasks list --view mine` non lo mostra più; `git log -1 --format=%s` inizia con `sb(tasks):`.

## S5 · `/sb:lint` e `/sb:lint --fix`

Setup:

    printf -- '---\ntype: topic\ntitle: On-call\n---\nNe parla spesso [[Luca]].\n' > knowledge/topics/On-call.md && git add -A && git commit -qm "setup S5"

Comandi: `/sb:lint`, poi `/sb:lint --fix`

Verifiche:
- dopo il primo comando, il report include `alias-link` per `On-call.md` e la source-note stantia; `git status --porcelain` è vuoto;
- dopo `--fix`, `On-call.md` contiene `[[Luca Bianchi|Luca]]` e `SB validate` non riporta più `alias-link`; `git log -1 --format=%s` inizia con `sb(lint):`.

## S6 · `/sb:schema add` (nuovo tipo + proposta applicata)

Comando: `/sb:schema add customer`. Rispondi: layer knowledge, cartella `knowledge/customers`, campo `account_manager` (link a person), nessun campo obbligatorio.

Verifiche:
- esiste `schema/types/customer.md` con `folder: knowledge/customers`;
- `schema/proposals.md` contiene una voce `- [x]`;
- `SB validate` → exit 0; `git log -1 --format=%s` inizia con `sb(schema):`.

## S7 · `/sb:sync --check` (sorgente irraggiungibile o inesistente)

Comando: `/sb:sync --check`

Verifiche:
- il report elenca `Confluence · Incident Management` come stantia, con esito "irraggiungibile" (la pagina di esempio non esiste) o "invariata/cambiata" se l'MCP risponde;
- in ogni caso `git status --porcelain` è vuoto.

## S8 · `/sb:init` (intervista + scaffold)

Setup: `T="$(mktemp -d)" && cd "$T" && git init -q -b main && claude --plugin-dir "$REPO"`

Comando: `/sb:init`. Rispondi all'intervista con un contesto inventato: 2 team e 3 persone, nessun remote.

Verifiche:
- `SB validate --wiki "$T"` → exit 0;
- esistono `schema/types/task.md`, `CLAUDE.md` e le pagine seed delle persone indicate;
- `git -C "$T" log -1 --format=%s` inizia con `sb(init):`.
````

- [ ] **Step 5: README finale**

Sostituisci `README.md` con:

````markdown
# Second Brain (`sb`)

Plugin Claude Code che trasforma Claude Code nel pannello di controllo di una **wiki LLM** per il lavoro di management. Si inseriscono note, documenti e pagine Confluence; Claude le organizza in una wiki Markdown strutturata e collegata (compatibile con Obsidian), che poi si interroga.

Design: [`docs/superpowers/specs/2026-10-02-second-brain-core-design.md`](docs/superpowers/specs/2026-10-02-second-brain-core-design.md)

## Requisiti

- Claude Code
- Python 3.9 o superiore (`python3`) e git
- Opzionali: i connettori MCP Atlassian (Confluence, Jira) e Microsoft 365 (mail)

## Installazione

In Claude Code:

    /plugin marketplace add minox86/second-brain
    /plugin install sb@second-brain

## Creare una wiki

Crea (o clona vuota) una cartella per la wiki, aprici Claude Code ed esegui `/sb:init`. Un'intervista genera lo schema partendo dal preset Head of Engineering.

## Comandi

| Comando | Scopo |
|---|---|
| `/sb:status` | Cruscotto: cosa richiede attenzione |
| `/sb:put <input>` | Fa entrare testo, file, Confluence, Jira, mail, web |
| `/sb:sync [sorgente] [--check]` | Riallinea le sorgenti esterne cambiate |
| `/sb:ask <domanda>` | Risposta puntuale con citazioni |
| `/sb:prep <target>` | Briefing per 1:1, riunione, persona, progetto |
| `/sb:report <tipo>` | Sintesi: settimana, mese, rischi, carico, upward, delegati |
| `/sb:tasks [vista \| azione]` | Vede e gestisce i task |
| `/sb:lint [--fix]` | Manutenzione |
| `/sb:schema [azione]` | Evoluzione dello schema |

Tutti i comandi si attivano anche in linguaggio naturale.

## Sviluppo

    python3 -m unittest discover -s tests -v     # test del toolkit
    claude plugin validate . --strict            # manifest e skill
    claude --plugin-dir .                        # prova locale del plugin

Gli scenari di accettazione delle skill sono in [`tests/scenarios/README.md`](tests/scenarios/README.md).
````

- [ ] **Step 6: Smoke test del plugin locale**

Run: `S="$(tests/scenarios/setup.sh)" && echo "$S"`, poi esegui lo scenario **S2** (sola lettura) e lo scenario **S4**.
Expected:
- i comandi `/sb:*` compaiono nell'autocompletamento;
- S2 risponde con le citazioni attese senza modificare la wiki;
- S4 chiude il task e fa commit.

Annota l'esito nel messaggio di commit. Se uno scenario fallisce, correggi la skill coinvolta e ripeti prima di procedere.

- [ ] **Step 7: Esegui tutti i test**

Run: `python3 -m unittest discover -s tests -v && claude plugin validate . --strict`
Expected: tutti `ok`; validate exit 0.

- [ ] **Step 8: Commit**

```bash
git add tests README.md
git commit -m "test: sample wiki, acceptance scenarios and README"
```
