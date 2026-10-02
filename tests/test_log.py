import datetime
import re
import unittest

from helpers import WikiCase, run_cli
from sb_core.log import LOG_HEADER, append_log

LINE = re.compile(r"^- \d{4}-\d{2}-\d{2} \d{2}:\d{2} · (\w+) · (.+)$")


class LogTest(WikiCase):
    def test_append_creates_and_appends(self):
        root = self.make_wiki()
        now = datetime.datetime(2026, 10, 2, 9, 30)
        result = append_log(root, "1:1 Luca\nBianchi:   2 task", op="put", now=now)
        self.assertEqual(result["logged"], "- 2026-10-02 09:30 · put · 1:1 Luca Bianchi: 2 task")
        append_log(root, "riallineate 3 sorgenti", op="sync", now=now)
        text = (root / "log.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith(LOG_HEADER))
        lines = [l for l in text.splitlines() if l.startswith("- ")]
        self.assertEqual([LINE.match(l).group(1) for l in lines], ["put", "sync"])

    def test_appends_after_file_without_trailing_newline(self):
        root = self.make_wiki({"log.md": "# Log\n\n- vecchia riga"})
        append_log(root, "nuova", now=datetime.datetime(2026, 10, 2, 9, 30))
        self.assertEqual((root / "log.md").read_text(encoding="utf-8").splitlines()[-2:],
                         ["- vecchia riga", "- 2026-10-02 09:30 · note · nuova"])

    def test_cli(self):
        root = self.make_wiki()
        code, data, _ = run_cli("log", "Ciao", "--op", "sync", "--wiki", root)
        self.assertEqual(code, 0)
        self.assertTrue(LINE.match(data["logged"]))
        self.assertEqual(run_cli("log", "   ", "--wiki", root)[0], 2)


if __name__ == "__main__":
    unittest.main()
