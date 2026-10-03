import datetime
import unittest

from helpers import WikiCase, md, run_cli
from sb_core.tasks import list_tasks
from sb_core.wiki import Wiki

TODAY = datetime.date(2026, 10, 2)

FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi"),
    "knowledge/projects/Migrazione DB.md": md("type: project\ntitle: Migrazione DB"),
    "operations/tasks/Mio scaduto.md": md(
        'type: task\ntitle: Mio scaduto\ndue: 2026-09-30\npriority: high\nrelated: ["[[Migrazione DB]]"]\ncreated: 2026-09-20'
    ),
    "operations/tasks/Mio oggi.md": md("type: task\ntitle: Mio oggi\nstatus: todo\ndue: 2026-10-02"),
    "operations/tasks/Mio senza data.md": md("type: task\ntitle: Mio senza data"),
    "operations/tasks/Delegato.md": md('type: task\ntitle: Delegato\nowner: "[[Luca Bianchi]]"\ndue: 2026-10-08\nstatus: blocked'),
    "operations/tasks/Chiuso.md": md("type: task\ntitle: Chiuso\nstatus: done\ndue: 2026-09-01"),
    "operations/tasks/Data sbagliata.md": md("type: task\ntitle: Data sbagliata\ndue: venerdì"),
}


class TasksTest(WikiCase):
    def setUp(self):
        self.root = self.make_wiki(FILES)
        self.wiki = Wiki(self.root)

    def titles(self, view, **kwargs):
        return [t["title"] for t in list_tasks(self.wiki, view=view, today=TODAY, **kwargs)]

    def test_views(self):
        self.assertEqual(self.titles("mine"), ["Mio scaduto", "Mio oggi", "Data sbagliata", "Mio senza data"])
        self.assertEqual(self.titles("delegated"), ["Delegato"])
        self.assertEqual(self.titles("overdue"), ["Mio scaduto"])
        self.assertEqual(self.titles("today"), ["Mio scaduto", "Mio oggi"])
        self.assertEqual(self.titles("week"), ["Mio scaduto", "Mio oggi", "Delegato"])
        self.assertEqual(self.titles("blocked"), ["Delegato"])
        self.assertEqual(len(self.titles("all")), 6)

    def test_filters(self):
        self.assertEqual(self.titles("all", project="Migrazione DB"), ["Mio scaduto"])
        self.assertEqual(self.titles("all", person="luca bianchi"), ["Delegato"])
        self.assertEqual(self.titles("all", priority="high"), ["Mio scaduto"])

    def test_record_contract(self):
        record = next(t for t in list_tasks(self.wiki, view="all", today=TODAY) if t["title"] == "Delegato")
        self.assertEqual(record, {
            "path": "operations/tasks/Delegato.md", "title": "Delegato", "status": "blocked",
            "owner": "Luca Bianchi", "delegated": True, "due": "2026-10-08", "overdue": False,
            "priority": None, "related": [], "created": None,
        })
        mine = next(t for t in list_tasks(self.wiki, view="all", today=TODAY) if t["title"] == "Mio scaduto")
        self.assertEqual((mine["status"], mine["overdue"], mine["related"], mine["created"]),
                         ("todo", True, ["Migrazione DB"], "2026-09-20"))

    def test_invalid_due_date_does_not_break(self):
        record = next(t for t in list_tasks(self.wiki, view="all", today=TODAY) if t["title"] == "Data sbagliata")
        self.assertEqual((record["due"], record["overdue"]), (None, False))

    def test_cli(self):
        code, data, _ = run_cli("tasks", "list", "--view", "overdue", "--today", "2026-10-02", "--json", "--wiki", self.root)
        self.assertEqual(code, 0)
        self.assertEqual([t["title"] for t in data["tasks"]], ["Mio scaduto"])
        self.assertEqual(data["view"], "overdue")
        self.assertIn("generated", data)
        code, _, _ = run_cli("tasks", "list", "--project", "[[Migrazione DB]]", "--view", "all", "--wiki", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(run_cli("tasks", "list", "--view", "boh", "--wiki", self.root)[0], 2)
        self.assertEqual(run_cli("tasks", "list", "--today", "ieri", "--wiki", self.root)[0], 2)


if __name__ == "__main__":
    unittest.main()
