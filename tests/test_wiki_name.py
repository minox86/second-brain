import unittest

from helpers import WikiCase, md, run_cli
from sb_core.board_api import Board
from sb_core.errors import WikiError
from sb_core.wiki import Wiki


class WikiNameTest(WikiCase):
    def test_defaults_to_the_folder_name(self):
        root = self.make_wiki()
        self.assertEqual(Wiki(root).name, root.resolve().name)

    def test_schema_wiki_md_sets_the_name(self):
        root = self.make_wiki({"schema/wiki.md": md("name: TeamSystem Engineering", "# Wiki\n")})
        self.assertEqual(Wiki(root).name, "TeamSystem Engineering")
        self.assertEqual(Board(root).snapshot()["wiki"]["name"], "TeamSystem Engineering")

    def test_blank_name_falls_back_to_the_folder(self):
        root = self.make_wiki({"schema/wiki.md": md('name: "  "')})
        self.assertEqual(Wiki(root).name, root.resolve().name)

    def test_non_text_name_is_an_error(self):
        with self.assertRaises(WikiError):
            Wiki(self.make_wiki({"schema/wiki.md": md("name: [a, b]")}))

    def test_version_reports_the_name(self):
        root = self.make_wiki({"schema/wiki.md": md("name: Second Brain HoE")})
        code, data, _ = run_cli("version", "--wiki", root)
        self.assertEqual((code, data["name"]), (0, "Second Brain HoE"))


if __name__ == "__main__":
    unittest.main()
