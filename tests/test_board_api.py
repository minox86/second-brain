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
            "status": ["todo", "blocked", "done", "dropped"],
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


class UpdateTest(WikiCase):
    def setUp(self):
        self.root = self.make_git_wiki(FILES)
        self.board = Board(self.root, today=lambda: TODAY)

    def etag(self, rel=T):
        return etag_of((self.root / rel).read_bytes())

    def committed_files(self):
        return sorted(p for p in git(self.root, "show", "--no-renames", "--name-only", "--format=", "HEAD").split("\n") if p)

    def test_updates_fields_surgically_and_commits_only_touched_files(self):
        (self.root / "knowledge/topics/Estraneo.md").write_text(md("type: topic\ntitle: Estraneo"), encoding="utf-8")
        result = self.board.update({"path": T, "etag": self.etag(),
                                    "set": {"priority": "high", "due": "2026-10-09", "owner": "Anna Neri"}})
        text = read(self.root, T)
        for fragment in ("# nota utente", "priority: high", 'owner: "[[Anna Neri]]"', "due: 2026-10-09",
                         "updated: 2026-10-02", 'related: ["[[Migrazione DB]]"]', "Contesto.\n"):
            self.assertIn(fragment, text)
        self.assertTrue(result["committed"])
        self.assertEqual(result["task"]["owner"], "Anna Neri")
        self.assertEqual(result["task"]["etag"], self.etag())
        self.assertEqual(self.committed_files(), sorted([T, "index.md", "log.md"]))
        self.assertTrue(git(self.root, "log", "-1", "--format=%s").startswith("sb(board): Stima → "))
        self.assertIn("Estraneo.md", git(self.root, "status", "--porcelain"))
        self.assertTrue(self.board.pusher.state()["pending_push"])

    def test_archive_flags_closed_tasks_and_hides_them(self):
        result = self.board.archive()
        self.assertEqual(result, {"archived": 1, "committed": True})
        text = read(self.root, "operations/tasks/Chiuso.md")
        self.assertIn("archived: true", text)
        self.assertIn("updated: 2026-10-02", text)
        self.assertNotIn("archived", read(self.root, T))
        self.assertEqual(self.committed_files(), sorted(["operations/tasks/Chiuso.md", "index.md", "log.md"]))
        self.assertEqual([t["title"] for t in self.board.snapshot()["tasks"]], ["Stima"])
        self.assertEqual(self.board.archive(), {"archived": 0, "committed": False})

    def test_null_removes_a_field(self):
        self.board.update({"path": T, "etag": self.etag(), "set": {"priority": None, "owner": None}})
        meta, _ = parse(read(self.root, T))
        self.assertNotIn("priority", meta)
        self.assertNotIn("owner", meta)

    def test_note_is_one_dated_line(self):
        self.board.update({"path": T, "etag": self.etag(), "note": "sollecitato\n  in   standup"})
        self.assertTrue(read(self.root, T).endswith("Contesto.\n- 2026-10-02: sollecitato in standup\n"))

    def test_stale_etag_is_a_conflict(self):
        before = (self.root / T).read_bytes()
        with self.assertRaises(Conflict) as ctx:
            self.board.update({"path": T, "etag": "vecchio", "set": {"priority": "high"}})
        self.assertEqual(ctx.exception.payload["task"]["path"], T)
        self.assertEqual((self.root / T).read_bytes(), before)

    def test_invalid_values_write_nothing(self):
        before = (self.root / T).read_bytes()
        for changes in ({"status": "wip"}, {"priority": "urgent"}, {"due": "venerdì"}, {"owner": "Nessuno"},
                        {"owner": "Migrazione DB"}, {"related": "Migrazione DB"}, {"related": ["Fantasma"]},
                        {"type": "risk"}, {}):
            with self.subTest(changes=changes):
                with self.assertRaises(Invalid):
                    self.board.update({"path": T, "etag": self.etag(), "set": changes})
                self.assertEqual((self.root / T).read_bytes(), before)

    def test_unknown_task_is_not_found(self):
        with self.assertRaises(NotFound):
            self.board.update({"path": "operations/tasks/Nessuno.md", "set": {"priority": "high"}})

    def test_retitle_rewrites_links_and_commits_the_rename(self):
        result = self.board.update({"path": T, "etag": self.etag(), "set": {"title": "Stima migrazione DB"}})
        new = "operations/tasks/Stima migrazione DB.md"
        self.assertEqual(result["task"]["path"], new)
        self.assertFalse((self.root / T).exists())
        self.assertIn("[[Stima migrazione DB]]", read(self.root, "knowledge/topics/On-call.md"))
        self.assertEqual(self.committed_files(), sorted([T, new, "knowledge/topics/On-call.md", "index.md", "log.md"]))

    def test_validation_failure_restores_the_file(self):
        before = (self.root / T).read_bytes()
        fake = Issue(T, "bad-value", "errore finto")
        with mock.patch("sb_core.board_api.validate", side_effect=[[], [fake]]):
            with self.assertRaises(Invalid) as ctx:
                self.board.update({"path": T, "etag": self.etag(), "set": {"priority": "high"}})
        self.assertEqual(ctx.exception.payload["issues"][0]["message"], "errore finto")
        self.assertEqual((self.root / T).read_bytes(), before)

    def test_failed_commit_is_retried_with_the_next_change(self):
        with mock.patch.object(self.board.git, "commit", side_effect=[(False, "hook"), (True, None)]) as commit:
            first = self.board.update({"path": T, "etag": self.etag(), "set": {"priority": "high"}})
            self.assertFalse(first["committed"])
            self.assertEqual(self.board.pending_commit, {T})
            self.assertEqual(self.board.sync_state()["commit_error"], "hook")
            self.board.update({"path": "operations/tasks/Chiuso.md",
                               "etag": self.etag("operations/tasks/Chiuso.md"), "set": {"status": "todo"}})
        self.assertIn(T, commit.call_args_list[1][0][0])
        self.assertEqual(self.board.pending_commit, set())

    def test_works_without_git(self):
        root = self.make_wiki(FILES)
        board = Board(root, today=lambda: TODAY)
        result = board.update({"path": T, "etag": etag_of((root / T).read_bytes()), "set": {"status": "blocked"}})
        self.assertEqual((result["committed"], result["task"]["status"]), (False, "blocked"))
        self.assertEqual(board.pending_commit, set())


class CreateTest(WikiCase):
    def setUp(self):
        self.root = self.make_git_wiki(FILES)
        self.board = Board(self.root, today=lambda: TODAY)

    def test_create_with_all_fields(self):
        result = self.board.create({"title": "Riunione con Nicolò", "status": "blocked", "priority": "high",
                                    "owner": "Luca", "related": ["Migrazione DB"], "due": "2026-10-10",
                                    "note": "dalla board"})
        rel = "operations/tasks/Riunione con Nicolò.md"
        meta, body = parse(read(self.root, rel))
        self.assertEqual(list(meta), ["type", "title", "status", "owner", "due", "priority", "related", "created"])
        self.assertEqual(meta["owner"], "[[Luca Bianchi]]")
        self.assertEqual(body, "- 2026-10-02: dalla board\n")
        self.assertEqual((result["committed"], result["task"]["path"]), (True, rel))

    def test_create_with_title_only(self):
        self.board.create({"title": "Solo titolo"})
        meta, body = parse(read(self.root, "operations/tasks/Solo titolo.md"))
        self.assertEqual((meta, body), ({"type": "task", "title": "Solo titolo", "created": "2026-10-02"}, ""))

    def test_invalid_title_and_values(self):
        for data in ({"title": "1:1 Luca"}, {"title": "  "}, {"title": "Ok", "owner": "Nessuno"},
                     {"title": "Ok", "status": "wip"}):
            with self.subTest(data=data):
                with self.assertRaises(Invalid):
                    self.board.create(data)
        self.assertFalse((self.root / "operations/tasks/Ok.md").exists())

    def test_duplicate_title_is_a_conflict(self):
        with self.assertRaises(Conflict) as ctx:
            self.board.create({"title": "stima"})
        self.assertEqual(ctx.exception.payload["path"], T)

    def test_validation_failure_removes_the_new_file(self):
        fake = Issue("x", "bad-value", "errore finto")
        with mock.patch("sb_core.board_api.validate", return_value=[fake]):
            with self.assertRaises(Invalid):
                self.board.create({"title": "Da buttare"})
        self.assertFalse((self.root / "operations/tasks/Da buttare.md").exists())


if __name__ == "__main__":
    unittest.main()
