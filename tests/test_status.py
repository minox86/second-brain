import datetime
import unittest

from helpers import WikiCase, md, run_cli
from sb_core.status import status
from sb_core.wiki import Wiki

TODAY = datetime.date(2026, 10, 2)


def one_on_one(day, person):
    return md(f'type: one-on-one\ntitle: {day} 1on1 {person}\nwith: "[[{person}]]"\ndate: {day}')


FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi"),
    "knowledge/people/Anna Neri.md": md("type: person\ntitle: Anna Neri"),
    "operations/tasks/Mio scaduto.md": md("type: task\ntitle: Mio scaduto\ndue: 2026-09-30"),
    "operations/tasks/In scadenza.md": md("type: task\ntitle: In scadenza\ndue: 2026-10-05"),
    "operations/tasks/Delegato in ritardo.md": md(
        'type: task\ntitle: Delegato in ritardo\nowner: "[[Luca Bianchi]]"\ndue: 2026-09-28'
    ),
    "operations/tasks/Delegato futuro.md": md('type: task\ntitle: Delegato futuro\nowner: "[[Anna Neri]]"\ndue: 2026-10-20'),
    "operations/one-on-ones/2026-08-01 1on1 Luca Bianchi.md": one_on_one("2026-08-01", "Luca Bianchi"),
    "operations/one-on-ones/2026-09-01 1on1 Luca Bianchi.md": one_on_one("2026-09-01", "Luca Bianchi"),
    "operations/one-on-ones/2026-09-25 1on1 Anna Neri.md": one_on_one("2026-09-25", "Anna Neri"),
    "schema/proposals.md": "# Proposte\n\n- [ ] P1 · vendor\n  - segnale: x\n- [x] P2 · fatto\n- [-] P3 · scartata\n- [ ] P4 · altro\n",
}


class StatusTest(WikiCase):
    def test_status(self):
        data = status(Wiki(self.make_wiki(FILES)), TODAY)
        titles = {k: [t["title"] for t in v] for k, v in data["tasks"].items()}
        self.assertEqual(titles, {
            "overdue": ["Mio scaduto"], "due_soon": ["In scadenza"], "delegated_overdue": ["Delegato in ritardo"],
        })
        self.assertEqual(data["one_on_one_gaps"], [{"person": "Luca Bianchi", "last": "2026-09-01", "days": 31}])
        self.assertEqual(data["open_proposals"], 2)
        self.assertEqual(data["stale_sources"], [])
        self.assertEqual(set(data["lint"]), {"errors", "warnings"})
        self.assertEqual(data["today"], "2026-10-02")

    def test_cli(self):
        code, data, _ = run_cli("status", "--today", "2026-10-02", "--wiki", self.make_wiki(FILES))
        self.assertEqual((code, data["open_proposals"]), (0, 2))


if __name__ == "__main__":
    unittest.main()
