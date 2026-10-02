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
