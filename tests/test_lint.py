import datetime
import unittest
from collections import Counter

from helpers import WikiCase, md, run_cli
from sb_core.lint import lint
from sb_core.wiki import Wiki

TODAY = datetime.date(2026, 10, 2)

FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi"),
    "knowledge/topics/Orfano.md": md("type: topic\ntitle: Orfano"),
    "knowledge/topics/Con link rotto.md": md("type: topic\ntitle: Con link rotto", "[[Fantasma]]\n"),
    "operations/tasks/Scaduto.md": md(
        'type: task\ntitle: Scaduto\ndue: 2026-09-01\nowner: "[[Luca Bianchi]]"\ncreated: 2026-09-01'
    ),
    "operations/risks/Rischio fermo.md": md(
        "type: risk\ntitle: Rischio fermo\nstatus: open\nupdated: 2026-08-01", "Riguarda [[Luca Bianchi]].\n"
    ),
    "operations/risks/Rischio chiuso.md": md(
        "type: risk\ntitle: Rischio chiuso\nstatus: closed\nupdated: 2026-01-01", "[[Luca Bianchi]]\n"
    ),
    "knowledge/sources/Vecchia.md": md(
        'type: source-note\ntitle: Vecchia\nexternal: "confluence:ENG/2"\nsynced: 2026-08-01', "Su [[Luca Bianchi]].\n"
    ),
}


class LintTest(WikiCase):
    def test_lint_codes(self):
        issues = lint(Wiki(self.make_wiki(FILES)), TODAY)
        self.assertEqual(Counter((i.path, i.code) for i in issues), Counter({
            ("knowledge/topics/Orfano.md", "orphan"): 1,
            ("knowledge/topics/Con link rotto.md", "broken-link"): 1,
            ("knowledge/topics/Con link rotto.md", "orphan"): 1,
            ("operations/tasks/Scaduto.md", "overdue-task"): 1,
            ("operations/tasks/Scaduto.md", "stale-item"): 1,
            ("operations/risks/Rischio fermo.md", "stale-item"): 1,
            ("knowledge/sources/Vecchia.md", "stale-source"): 1,
        }))
        severities = {i.code: i.severity for i in issues}
        self.assertEqual(severities["broken-link"], "error")
        self.assertEqual(severities["orphan"], "warning")

    def test_cli(self):
        code, data, _ = run_cli("lint", "--today", "2026-10-02", "--wiki", self.make_wiki(FILES))
        self.assertEqual((code, data["ok"], data["summary"]["orphan"]), (1, False, 2))
        code, data, _ = run_cli("lint", "--today", "2026-10-02", "--wiki", self.make_wiki())
        self.assertEqual((code, data["ok"], data["summary"]), (0, True, {}))


if __name__ == "__main__":
    unittest.main()
