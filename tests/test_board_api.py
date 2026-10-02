import datetime
import os
import unittest
from unittest import mock

from helpers import WikiCase, git, md
from sb_core.board_api import Board, Conflict, Invalid, NotFound, etag_of
from sb_core.frontmatter import parse
from sb_core.validate import Issue

TODAY = datetime.date(2026, 10, 2)
T = "operations/tasks/Stima.md"
FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi\naliases: [Luca]"),
    "knowledge/people/Anna Neri.md": md("type: person\ntitle: Anna Neri"),
    "knowledge/people/Ex Collega.md": md("type: person\ntitle: Ex Collega\nstatus: left"),
    "knowledge/projects/Migrazione DB.md": md("type: project\ntitle: Migrazione DB"),
    "knowledge/topics/On-call.md": md("type: topic\ntitle: On-call", "Vedi [[Stima]].\n"),
    T: md(
        'type: task\ntitle: Stima\n# nota utente\nowner: "[[Luca Bianchi]]"\npriority: low\n'
        'related: ["[[Migrazione DB]]"]\ncreated: 2026-09-15',
        "Contesto.\n",
    ),
    "operations/tasks/Chiuso.md": md("type: task\ntitle: Chiuso\nstatus: done\nupdated: 2026-09-30"),
}


def read(root, rel):
    return (root / rel).read_text(encoding="utf-8")


class SnapshotTest(WikiCase):
    def test_snapshot_shape(self):
        root = self.make_wiki(FILES)
        snap = Board(root, today=lambda: TODAY).snapshot()
        self.assertEqual(set(snap), {"wiki", "today", "thresholds", "enums", "tasks", "people", "projects", "sync"})
        self.assertEqual(snap["wiki"]["name"], root.resolve().name)
        self.assertEqual(snap["today"], "2026-10-02")
        self.assertEqual(snap["thresholds"]["due_soon_days"], 7)
        self.assertEqual(snap["enums"], {
            "status": ["todo", "doing", "blocked", "done", "dropped"],
            "priority": ["low", "medium", "high"],
            "closed": ["done", "dropped"],
        })
        self.assertEqual([p["title"] for p in snap["people"]], ["Anna Neri", "Luca Bianchi"])
        self.assertEqual(snap["projects"], [{"title": "Migrazione DB", "path": "knowledge/projects/Migrazione DB.md"}])
        self.assertFalse(snap["sync"]["git"])

    def test_task_records(self):
        root = self.make_wiki(FILES)
        tasks = {t["title"]: t for t in Board(root, today=lambda: TODAY).snapshot()["tasks"]}
        stima = tasks["Stima"]
        self.assertEqual(stima["owner"], "Luca Bianchi")
        self.assertEqual(stima["related"], ["Migrazione DB"])
        self.assertEqual(stima["body"], "Contesto.\n")
        self.assertEqual(stima["etag"], etag_of((root / T).read_bytes()))
        self.assertIsNone(stima["updated"])
        self.assertEqual(tasks["Chiuso"]["updated"], "2026-09-30")

    def test_sync_state_in_git_wiki(self):
        root = self.make_git_wiki(FILES)
        sync = Board(root).snapshot()["sync"]
        self.assertTrue(sync["git"])
        self.assertEqual(sync["head"], git(root, "rev-parse", "--short", "HEAD").strip())
        self.assertEqual((sync["pending_push"], sync["uncommitted"]), (False, []))

    def test_version_changes_when_a_task_changes(self):
        root = self.make_wiki(FILES)
        board = Board(root)
        before = board.version()["version"]
        self.assertEqual(board.version()["version"], before)
        stat = (root / T).stat()
        os.utime(str(root / T), ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
        self.assertNotEqual(board.version()["version"], before)


if __name__ == "__main__":
    unittest.main()
