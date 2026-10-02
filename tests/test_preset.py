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
