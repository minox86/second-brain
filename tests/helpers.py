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
