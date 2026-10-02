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
