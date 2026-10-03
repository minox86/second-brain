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

    def css_rule(self, selector):
        match = re.search(re.escape(selector) + r"\{([^}]*)\}", self.text)
        self.assertIsNotNone(match, selector)
        return match.group(1)

    def test_board_never_scrolls_horizontally(self):
        self.assertNotIn("overflow-x", self.css_rule(".board"))
        self.assertIn("min-width:0", self.css_rule(".col"))
        self.assertIn("flex-wrap:nowrap", self.css_rule(".meta"))

    def test_cards_never_shrink_below_their_content(self):
        # con overflow:hidden un elemento flex in colonna può schiacciarsi a 0: la lane deve scorrere
        self.assertIn("flex-shrink:0", self.css_rule(".card"))

    def test_long_labels_are_truncated(self):
        chip = self.css_rule(".chip")
        for prop in ("overflow:hidden", "text-overflow:ellipsis", "white-space:nowrap"):
            self.assertIn(prop, chip)
        self.assertIn("-webkit-line-clamp:3", self.css_rule(".ttl"))

    def test_card_follows_layout_b(self):
        # priorità cliccabile in testa, stream accanto, check a destra, titolo grande, persona e scadenza in fondo
        for marker in ('class="pill ', 'data-action="prio-cycle"', 'class="stream"', 'class="check"',
                       'data-action="toggle"', 'class="person"', "function streamOf("):
            self.assertIn(marker, self.text)
        self.assertNotIn(".card.p-high::before", self.text)
        self.assertIn("font-size:14px", self.css_rule(".ttl"))

    def test_closed_cards_are_not_struck_through(self):
        self.assertNotIn("line-through", self.text)

    def test_only_three_statuses_are_labelled(self):
        self.assertNotIn("doing:", self.text)
        self.assertNotIn("In corso", self.text)

    def test_undo_with_ctrl_z(self):
        for marker in ("function undo()", "history.push(entry)", "e.key.toLowerCase() === 'z'", "patch(h.path, h.set, null, true)"):
            self.assertIn(marker, self.text)

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
