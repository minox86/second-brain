import unittest
from collections import Counter

from helpers import WikiCase, md, run_cli
from sb_core.errors import WikiError
from sb_core.validate import validate
from sb_core.wiki import Wiki

GOOD = {
    "knowledge/people/Luca Bianchi.md": md(
        'type: person\ntitle: Luca Bianchi\naliases: [Luca]\nteam: "[[Platform]]"', "Lavora con [[Platform]].\n"
    ),
    "knowledge/teams/Platform.md": md("type: team\ntitle: Platform"),
    "operations/tasks/Chiedere la stima.md": md(
        'type: task\ntitle: Chiedere la stima\nstatus: todo\nowner: "[[Luca Bianchi|Luca]]"\n'
        'due: 2026-10-09\nrelated: ["[[Platform]]"]\ncreated: 2026-10-02'
    ),
}


class ValidateTest(WikiCase):
    def codes(self, files, paths=None):
        wiki = Wiki(self.make_wiki(files))
        return Counter((i.path, i.code) for i in validate(wiki, paths))

    def test_valid_wiki(self):
        self.assertEqual(self.codes(GOOD), Counter())

    def test_frontmatter_problems(self):
        self.assertEqual(self.codes({
            "knowledge/people/A.md": "senza frontmatter",
            "knowledge/people/B.md": "---\ntitle: [\n---\n",
        }), Counter({("knowledge/people/A.md", "no-frontmatter"): 1, ("knowledge/people/B.md", "bad-frontmatter"): 1}))

    def test_type_title_and_folder(self):
        self.assertEqual(self.codes({
            "knowledge/people/X.md": md("title: X"),
            "knowledge/people/Y.md": md("type: martian\ntitle: Y"),
            "knowledge/people/Z.md": md("type: person"),
            "knowledge/people/W.md": md("type: person\ntitle: Altro nome"),
            "knowledge/teams/V.md": md("type: person\ntitle: V"),
            "knowledge/people/K.md": md('type: person\ntitle: "K: x"'),
        }), Counter({
            ("knowledge/people/X.md", "missing-type"): 1,
            ("knowledge/people/Y.md", "unknown-type"): 1,
            ("knowledge/people/Z.md", "missing-title"): 1,
            ("knowledge/people/W.md", "filename-mismatch"): 1,
            ("knowledge/teams/V.md", "wrong-folder"): 1,
            ("knowledge/people/K.md", "bad-title"): 1,
        }))

    def test_field_values(self):
        files = dict(GOOD)
        files["operations/tasks/T.md"] = md(
            'type: task\ntitle: T\nstatus: wip\ndue: venerdì\npriority: urgent\n'
            'owner: Luca Bianchi\nrelated: "[[Platform]]"\nestimate: 3'
        )
        self.assertEqual(self.codes(files), Counter({
            ("operations/tasks/T.md", "bad-value"): 5,
            ("operations/tasks/T.md", "unknown-field"): 1,
        }))

    def test_links(self):
        files = dict(GOOD)
        files["operations/tasks/T.md"] = md(
            'type: task\ntitle: T\nowner: "[[Platform]]"\nrelated: ["[[Nessuno]]"]',
            "Vedi [[Luca]], [[Fantasma]] e [[#sezione]].\n",
        )
        self.assertEqual(self.codes(files), Counter({
            ("operations/tasks/T.md", "wrong-link-type"): 1,
            ("operations/tasks/T.md", "broken-link"): 2,
            ("operations/tasks/T.md", "alias-link"): 1,
        }))

    def test_duplicate_titles_are_case_insensitive(self):
        self.assertEqual(self.codes({
            "knowledge/people/Luca.md": md("type: person\ntitle: Luca"),
            "knowledge/teams/luca.md": md("type: team\ntitle: luca"),
        }), Counter({
            ("knowledge/people/Luca.md", "duplicate-title"): 1,
            ("knowledge/teams/luca.md", "duplicate-title"): 1,
        }))

    def test_common_fields(self):
        self.assertEqual(self.codes({
            "knowledge/sources/S.md": md(
                'type: source-note\ntitle: S\nexternal: "notion:abc"\nsynced: ieri\nauthority: external\naliases: Luca'
            ),
            "knowledge/sources/T.md": md('type: source-note\ntitle: T\nexternal: "confluence:ENG/1"\nsynced: 2026-10-01'),
            "knowledge/sources/U.md": md('type: source-note\ntitle: U\nexternal: "url:https://example.com/a"'),
        }), Counter({
            ("knowledge/sources/S.md", "unknown-source"): 1,
            ("knowledge/sources/S.md", "bad-value"): 3,
        }))

    def test_required_fields(self):
        self.assertEqual(self.codes({"operations/one-on-ones/O.md": md("type: one-on-one\ntitle: O")}),
                         Counter({("operations/one-on-ones/O.md", "missing-required"): 2}))

    def test_paths_filter(self):
        files = dict(GOOD)
        files["knowledge/people/X.md"] = md("title: X")
        self.assertEqual(self.codes(files, ["knowledge/teams/Platform.md"]), Counter())
        wiki = Wiki(self.make_wiki(GOOD))
        with self.assertRaises(WikiError):
            validate(wiki, ["knowledge/people/Nessuno.md"])

    def test_cli(self):
        root = self.make_wiki(GOOD)
        code, data, _ = run_cli("validate", "--wiki", root)
        self.assertEqual((code, data["ok"], data["checked"]), (0, True, 3))
        (root / "knowledge" / "people" / "X.md").write_text(md("title: X"), encoding="utf-8")
        code, data, _ = run_cli("validate", "--wiki", root)
        self.assertEqual((code, data["ok"]), (1, False))
        self.assertEqual(data["issues"][0]["code"], "missing-type")
        code, data, _ = run_cli("validate", "--wiki", root, str(root / "knowledge" / "teams" / "Platform.md"))
        self.assertEqual((code, data["checked"]), (0, 1))
        code, data, _ = run_cli("validate", "--wiki", self.make_wiki(base=False))
        self.assertEqual(code, 2)
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
