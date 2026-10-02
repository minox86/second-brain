import json
import unittest

from helpers import ROOT

import sb_core
from sb_core.frontmatter import parse


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

    def test_all_commands_present(self):
        names = {p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")}
        self.assertEqual(names, {"init", "status", "put", "sync", "ask", "prep", "report", "tasks", "lint", "schema",
                                 "board"})

    def test_tasks_skill_uses_deterministic_commands(self):
        text = (SKILLS_DIR / "tasks" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("SB tasks add", text)
        self.assertIn("SB tasks update", text)

    def test_board_skill_controls_the_server(self):
        text = (SKILLS_DIR / "board" / "SKILL.md").read_text(encoding="utf-8")
        for marker in ("SB board", ".sb/board.json", "SIGTERM", "run_in_background"):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
