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
        for marker in ('data-view="status"', 'data-view="priority"', 'data-view="people"', 'data-view="projects"', "Aggiungi task",
                       "draggable", "Aggiungi nota", "Comando per Claude", "Nuovo task"):
            self.assertIn(marker, self.text)

    def test_archive_button(self):
        for marker in ('data-action="archive"', "Archivia tutti", "case 'archive': archiveClosed()", "function archiveClosed(", "api('POST', '/api/tasks/archive')"):
            self.assertIn(marker, self.text)

    def test_palette(self):
        for color in ("#F2ECE3", "#F6F1EA", "#FBF8F3", "#A2461E", "#ECE4D8", "#EFE3CC", "#F1DED4", "#E5E5D4", "#E8E3DB"):
            self.assertIn(color, self.text)

    def css_rule(self, selector):
        match = re.search(re.escape(selector) + r"\{([^}]*)\}", self.text)
        self.assertIsNotNone(match, selector)
        return match.group(1)

    def test_three_to_five_columns_fill_the_width(self):
        # più di 5 colonne scorrono, meno di 3 restano larghe un terzo
        self.assertIn("overflow-x:auto", self.css_rule(".board"))
        col = self.css_rule(".col")
        for prop in ("flex:1 0 0", "min-width:calc((100% - 40px) / 5)", "max-width:calc((100% - 20px) / 3)"):
            self.assertIn(prop, col)
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

    def test_panel_follows_option_a(self):
        # testata con badge e titolo a capo, campi con icona, contesto per tipo, descrizione e cronologia separate, fonti
        for marker in ('class="tbadge"', '<textarea id="p-title" class="p-title" data-field="title"', 'class="facts"',
                       "fact('p-status', 'Stato'", "fact('p-prio', 'Priorità'", "fact('p-due', 'Scadenza'", "fact('p-owner'",
                       "<h3>Contesto</h3>", 'class="ctx-l"', "function relChip(", "<h3>Descrizione</h3>", "<h3>Cronologia</h3>",
                       "<h3>Fonti</h3>", "function splitBody(", "function inline(", "function pageType(", "S.snap.page_types"):
            self.assertIn(marker, self.text)
        self.assertNotIn('class="p-fields"', self.text)
        # la textarea del titolo si misura da visibile, altrimenti resta alta zero
        self.assertIn("panel.hidden = false;\n    autosize($('p-title'));", self.text)

    def test_click_outside_closes_the_panel(self):
        self.assertIn("if (S.selected && !e.target.closest('#panel, .card, #menu, #modal')", self.text)

    def test_page_types_share_icon_and_colour(self):
        for t in ("project", "team", "person", "task", "decision", "risk", "meeting", "'one-on-one'", "goal", "idea",
                  "system", "topic", "process", "vendor", "'source-note'", "other"):
            self.assertIn(t + ": { one: '", self.text)
        self.assertIn("var TYPE_ORDER = Object.keys(TYPE);", self.text)

    def test_card_stream_shows_only_the_project(self):
        self.assertIn("function streamOf(t) { return projectOf(t); }", self.text)
        self.assertNotIn("people.indexOf(r) < 0 && r !== t.owner", self.text)
        self.assertNotIn(".card.p-high::before", self.text)
        self.assertIn("font-size:14px", self.css_rule(".ttl"))

    def test_has_inline_favicon(self):
        # inline: il browser non chiede /favicon.ico al server della board
        self.assertIn('<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,', self.text)

    def test_no_show_closed_toggle(self):
        self.assertNotIn("Mostra chiusi", self.text)
        self.assertNotIn("showClosed", self.text)

    def test_sorting_is_by_priority_then_due_in_every_view(self):
        self.assertIn("return rank(a.priority) - rank(b.priority) || byDue(a, b)", self.text)
        self.assertNotIn("if (S.view === 'priority') {\n      var projects = ", self.text)

    def test_priority_is_the_default_view(self):
        self.assertIn("view: store.get('view', 'priority')", self.text)
        self.assertIn("if (VIEWS.indexOf(S.view) < 0) S.view = 'priority';", self.text)
        self.assertIn('data-view="priority" aria-pressed="true">Priorità<kbd>1</kbd>', self.text)
        self.assertLess(self.text.index('data-view="priority"'), self.text.index('data-view="status"'))
        self.assertNotIn('data-view="status" aria-pressed="true"', self.text)

    def test_projects_view_has_one_column_per_project_with_tasks(self):
        for marker in ("var VIEWS = ['priority', 'status', 'people', 'projects'];", "S.view === 'projects'",
                       "Progetti<kbd>4</kbd>", "key: 'j:' + pr", "'Senza progetto'", "function projectOf(",
                       "if (col.field === 'project') {", "setView(VIEWS[+k - 1])"):
            self.assertIn(marker, self.text)
        # le colonne nascono solo dai progetti che hanno task aperti, non dall'elenco dei progetti
        self.assertIn("open.forEach(function (t) { var pr = projectOf(t);", self.text)

    def test_closed_cards_are_not_struck_through(self):
        self.assertNotIn("line-through", self.text)

    def test_only_three_statuses_are_labelled(self):
        self.assertNotIn("doing:", self.text)
        self.assertNotIn("In corso", self.text)

    def test_undo_with_ctrl_z(self):
        for marker in ("function undo()", "history.push(entry)", "e.key.toLowerCase() === 'z'", "patch(h.path, h.set, null, true)"):
            self.assertIn(marker, self.text)

    def test_title_is_editable_inline(self):
        for marker in ('class="ttl-edit"', 'data-action="edit-title"', "function commitTitle(", "function startEdit(",
                       "case 'edit-title':"):
            self.assertIn(marker, self.text)
        self.assertNotIn("'dblclick'", self.text)

    def test_quick_add_has_priority_project_and_person(self):
        for marker in ('id="qadd-prio"', 'id="qadd-project"', 'id="qadd-owner"', "function quickAddFields("):
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
