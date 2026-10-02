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
