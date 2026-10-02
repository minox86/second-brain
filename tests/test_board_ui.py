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
