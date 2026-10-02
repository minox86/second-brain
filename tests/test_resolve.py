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
