import unittest

import helpers  # noqa: F401  (configura sys.path)
from sb_core.errors import FrontmatterError
from sb_core.frontmatter import dump, parse, render


class ParseTest(unittest.TestCase):
    def test_scalars(self):
        meta, body = parse(
            "---\ntitle: Luca Bianchi\nversion: 42\nratio: 0.5\nactive: true\n"
            "none: null\ncreated: 2026-10-02\n---\nCorpo\n"
        )
        self.assertEqual(meta, {
            "title": "Luca Bianchi", "version": 42, "ratio": 0.5, "active": True,
            "none": None, "created": "2026-10-02",
        })
        self.assertEqual(body, "Corpo\n")

    def test_no_frontmatter(self):
        self.assertEqual(parse("# Titolo\n"), (None, "# Titolo\n"))

    def test_empty_frontmatter(self):
        self.assertEqual(parse("---\n---\nx"), ({}, "x"))

    def test_unclosed(self):
        with self.assertRaises(FrontmatterError):
            parse("---\ntitle: x\n")

    def test_flow_lists_with_quoted_wikilinks(self):
        meta, _ = parse(
            '---\nrelated: ["[[Migrazione DB]]", "[[2026-10-02 1on1 Luca]]"]\n'
            'sources: [raw/2026/10/x, "jira:PLAT-123", jira:PLAT-9]\n---\n'
        )
        self.assertEqual(meta["related"], ["[[Migrazione DB]]", "[[2026-10-02 1on1 Luca]]"])
        self.assertEqual(meta["sources"], ["raw/2026/10/x", "jira:PLAT-123", "jira:PLAT-9"])

    def test_unquoted_wikilinks_like_obsidian(self):
        meta, _ = parse('---\nowner: [[Luca Bianchi]]\nrelated:\n  - [[A]]\n  - "[[B|b]]"\n---\n')
        self.assertEqual(meta["owner"], "[[Luca Bianchi]]")
        self.assertEqual(meta["related"], ["[[A]]", "[[B|b]]"])

    def test_block_mapping_with_flow_maps(self):
        meta, _ = parse(
            "---\nname: person\nfields:\n  role: {kind: string}\n"
            "  status: {kind: enum, values: [active, left], default: active}\n---\n"
        )
        self.assertEqual(meta["fields"], {
            "role": {"kind": "string"},
            "status": {"kind": "enum", "values": ["active", "left"], "default": "active"},
        })

    def test_nested_flow_map(self):
        meta, _ = parse("---\nsources:\n  conf-eng: {system: confluence, scope: ENG, covers: [process]}\n---\n")
        self.assertEqual(meta["sources"]["conf-eng"], {"system": "confluence", "scope": "ENG", "covers": ["process"]})

    def test_empty_collections(self):
        meta, _ = parse("---\na: []\nb: {}\nc:\n---\n")
        self.assertEqual(meta, {"a": [], "b": {}, "c": None})

    def test_comments(self):
        meta, _ = parse('---\n# commento\nstatus: todo   # stato\ntitle: "Issue #12"\nnote: C#\n---\n')
        self.assertEqual(meta, {"status": "todo", "title": "Issue #12", "note": "C#"})

    def test_apostrophe_in_unquoted_text(self):
        meta, _ = parse("---\ntitle: L'idea di Luca # nota\n---\n")
        self.assertEqual(meta["title"], "L'idea di Luca")

    def test_single_and_double_quotes(self):
        meta, _ = parse("---\na: 'It''s ok'\nb: \"riga\\nnuova \\\"x\\\"\"\n---\n")
        self.assertEqual(meta, {"a": "It's ok", "b": 'riga\nnuova "x"'})

    def test_colon_in_unquoted_value(self):
        meta, _ = parse("---\nnote: Ore 10: standup\n---\n")
        self.assertEqual(meta["note"], "Ore 10: standup")

    def test_crlf_and_bom(self):
        self.assertEqual(parse("\ufeff---\r\ntitle: X\r\n---\r\nCorpo\r\n"), ({"title": "X"}, "Corpo\n"))

    def test_errors(self):
        for bad in [
            "---\n  indent: x\n---\n",
            "---\nlist: [a, b\n---\n",
            "---\nnokey\n---\n",
            "---\nm:\n  - a\n  b: c\n---\n",
            "---\nm:\n  b:\n---\n",
            '---\na: "aperta\n---\n',
        ]:
            with self.subTest(bad=bad):
                with self.assertRaises(FrontmatterError):
                    parse(bad)


class DumpTest(unittest.TestCase):
    def test_round_trip(self):
        meta = {
            "type": "task", "title": "Chiedere a Luca, subito", "owner": "[[Luca Bianchi]]",
            "due": "2026-10-09", "version": 42, "done": False,
            "related": ["[[Migrazione DB]]", "jira:PLAT-1"],
            "fields": {"status": {"kind": "enum", "values": ["a", "b"]}},
            "empty": None, "note": "Issue #12", "num_string": "42", "colon": "Ore 10: standup",
            "quote": 'detto "ciao"',
        }
        self.assertEqual(parse(render(meta, "Corpo\n")), (meta, "Corpo\n"))

    def test_plain_strings_stay_unquoted(self):
        self.assertEqual(
            dump({"title": "Luca Bianchi", "created": "2026-10-02", "sources": ["raw/2026/10/x"]}),
            "title: Luca Bianchi\ncreated: 2026-10-02\nsources: [raw/2026/10/x]\n",
        )

    def test_wikilinks_are_quoted(self):
        self.assertEqual(dump({"owner": "[[Luca]]"}), 'owner: "[[Luca]]"\n')


if __name__ == "__main__":
    unittest.main()
