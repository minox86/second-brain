import json
import unittest

from helpers import WikiCase, md, run_cli
from sb_core.index import write_index
from sb_core.links import graph
from sb_core.wiki import Wiki

FILES = {
    "knowledge/people/Luca Bianchi.md": md(
        'type: person\ntitle: Luca Bianchi\nupdated: 2026-10-02\nteam: "[[Platform]]"',
        "Lavora con [[Platform]] e cita sé stesso: [[Luca Bianchi]].\n",
    ),
    "knowledge/teams/Platform.md": md("type: team\ntitle: Platform", "Link rotto: [[Fantasma]].\n"),
    "operations/tasks/Chiedere la stima.md": md(
        'type: task\ntitle: Chiedere la stima\nowner: "[[Luca Bianchi]]"\nrelated: ["[[Platform]]"]\ncreated: 2026-10-01'
    ),
}


class IndexTest(WikiCase):
    def test_index_content(self):
        root = self.make_wiki(FILES)
        result = write_index(Wiki(root))
        text = (root / "index.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Indice"))
        self.assertIn("## knowledge\n\n### person (1)\n- [[Luca Bianchi]] · 2026-10-02\n\n### team (1)\n- [[Platform]]\n", text)
        self.assertIn("## operations\n\n### task (1)\n- [[Chiedere la stima]] · 2026-10-01\n", text)
        self.assertNotIn("## outputs", text)
        self.assertEqual(result, {"pages": 3, "index": "index.md", "backlinks": ".sb/backlinks.json"})

    def test_backlinks_file(self):
        root = self.make_wiki(FILES)
        write_index(Wiki(root))
        backlinks = json.loads((root / ".sb" / "backlinks.json").read_text(encoding="utf-8"))
        self.assertEqual(backlinks, {
            "knowledge/people/Luca Bianchi.md": ["operations/tasks/Chiedere la stima.md"],
            "knowledge/teams/Platform.md": ["knowledge/people/Luca Bianchi.md", "operations/tasks/Chiedere la stima.md"],
        })

    def test_graph_ignores_self_and_broken_links(self):
        outgoing, incoming = graph(Wiki(self.make_wiki(FILES)))
        self.assertEqual(outgoing["knowledge/people/Luca Bianchi.md"], {"knowledge/teams/Platform.md"})
        self.assertEqual(outgoing["knowledge/teams/Platform.md"], set())
        self.assertEqual(incoming["operations/tasks/Chiedere la stima.md"], set())

    def test_cli(self):
        root = self.make_wiki(FILES)
        code, data, _ = run_cli("index", "--wiki", root)
        self.assertEqual((code, data["pages"]), (0, 3))
        self.assertTrue((root / "index.md").is_file())


if __name__ == "__main__":
    unittest.main()
