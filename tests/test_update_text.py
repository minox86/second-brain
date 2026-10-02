import unittest

import helpers  # noqa: F401
from sb_core.frontmatter import parse, update_text

SRC = (
    "---\n"
    "# commento dell'utente\n"
    "type: task\n"
    "title: Stima   # titolo\n"
    "related:\n"
    '  - "[[A]]"\n'
    '  - "[[B]]"\n'
    "priority: low\n"
    "---\n"
    "Corpo\n"
)


class UpdateTextTest(unittest.TestCase):
    def test_replaces_only_the_changed_line(self):
        out = update_text(SRC, {"priority": "high"})
        self.assertEqual(out, SRC.replace("priority: low", "priority: high"))

    def test_replaces_a_whole_block(self):
        out = update_text(SRC, {"related": ["[[C]]"]})
        self.assertEqual(out, SRC.replace('related:\n  - "[[A]]"\n  - "[[B]]"\n', 'related: ["[[C]]"]\n'))
        self.assertIn("# commento dell'utente", out)

    def test_removes_with_none(self):
        out = update_text(SRC, {"priority": None})
        self.assertNotIn("priority", out)
        self.assertEqual(parse(out)[0]["title"], "Stima")

    def test_appends_new_fields_before_closing(self):
        out = update_text(SRC, {"due": "2026-10-09", "owner": "[[Luca Bianchi]]"})
        self.assertTrue(out.endswith('priority: low\ndue: 2026-10-09\nowner: "[[Luca Bianchi]]"\n---\nCorpo\n'))

    def test_multiple_changes_and_round_trip(self):
        out = update_text(SRC, {"priority": None, "related": None, "status": "done"})
        meta, body = parse(out)
        self.assertEqual(meta, {"type": "task", "title": "Stima", "status": "done"})
        self.assertEqual(body, "Corpo\n")

    def test_without_frontmatter(self):
        self.assertEqual(update_text("Corpo\n", {"type": "task", "x": None}), "---\ntype: task\n---\nCorpo\n")
        self.assertEqual(update_text("Corpo\n", {"x": None}), "Corpo\n")

    def test_empty_frontmatter(self):
        self.assertEqual(update_text("---\n---\nx", {"a": 1}), "---\na: 1\n---\nx")

    def test_crlf_input_is_normalised(self):
        out = update_text("---\r\ntitle: T\r\n---\r\nCorpo\r\n", {"title": "U"})
        self.assertEqual(out, "---\ntitle: U\n---\nCorpo\n")


if __name__ == "__main__":
    unittest.main()
