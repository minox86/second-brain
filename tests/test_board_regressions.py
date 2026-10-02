"""Regressioni emerse dalla revisione finale della board."""
import datetime
import json
import os
import threading
import time
import unicodedata
import unittest
from unittest import mock

from helpers import ROOT, WikiCase, git, md, run_cli
from sb_core.board_api import Board, Invalid, etag_of
from sb_core.board_server import STATE_FILE, running_board
from sb_core.gitops import PushScheduler

TODAY = datetime.date(2026, 10, 2)
PERSON = {"knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi")}


class CommitPathsTest(WikiCase):
    def test_accented_rename_leaves_a_clean_tree(self):
        root = self.make_git_wiki(PERSON)
        board = Board(root, today=lambda: TODAY)
        created = board.create({"title": "Riunione con Nicolò"})["task"]
        board.update({"path": created["path"], "etag": created["etag"], "set": {"title": "Riunione con Nicolò bis"}})
        self.assertEqual(git(root, "status", "--porcelain", "--", "knowledge", "operations", "index.md", "log.md").strip(), "")

    def test_case_only_rename_commits_and_does_not_block_later_commits(self):
        root = self.make_git_wiki(dict(PERSON, **{"operations/tasks/Old.md": md("type: task\ntitle: Old")}))
        board = Board(root, today=lambda: TODAY)
        rel = "operations/tasks/Old.md"
        result = board.update({"path": rel, "etag": etag_of((root / rel).read_bytes()), "set": {"title": "old"}})
        self.assertTrue(result["committed"], board.last_commit_error)
        second = board.create({"title": "Dopo"})
        self.assertTrue(second["committed"], board.last_commit_error)
        self.assertEqual(git(root, "status", "--porcelain", "--", "knowledge", "operations", "index.md", "log.md").strip(), "")

    def test_pending_paths_do_not_poison_the_next_commit(self):
        root = self.make_git_wiki(PERSON)
        board = Board(root, today=lambda: TODAY)
        board.pending_commit.add("operations/tasks/Sparito.md")
        real = board.git.commit
        calls = []

        def flaky(paths, message):
            calls.append(list(paths))
            if "operations/tasks/Sparito.md" in paths:
                return False, "pathspec non trovato"
            return real(paths, message)

        with mock.patch.object(board.git, "commit", side_effect=flaky):
            result = board.create({"title": "Nuovo"})
        self.assertTrue(result["committed"])
        self.assertEqual(len(calls), 2)


class NfdPathTest(WikiCase):
    def test_cli_update_finds_nfd_file(self):
        nfd = unicodedata.normalize("NFD", "Riunione con Nicolò")
        root = self.make_git_wiki(dict(PERSON, **{f"operations/tasks/{nfd}.md": md(f"type: task\ntitle: {nfd}")}))
        code, data, _ = run_cli("tasks", "update", "operations/tasks/Riunione con Nicolò.md",
                                "--set", "priority=high", "--wiki", root)
        self.assertEqual(code, 0, data)


class StaleStateTest(WikiCase):
    def test_live_unrelated_pid_is_not_a_board(self):
        root = self.make_wiki(PERSON)
        (root / ".sb").mkdir(exist_ok=True)
        (root / STATE_FILE).write_text(json.dumps({"pid": os.getpid(), "port": 9, "url": "http://127.0.0.1:9/?t=x"}),
                                       encoding="utf-8")
        self.assertIsNone(running_board(root))

    def test_board_skill_checks_the_api_before_killing(self):
        text = (ROOT / "skills" / "board" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("/api/version", text.split("## `stop`", 1)[1].split("## `status`", 1)[0])


class PushRaceTest(unittest.TestCase):
    def test_mark_during_push_keeps_pending(self):
        class SlowGit(object):
            def has_remote(self):
                return True

            def push(self):
                time.sleep(0.3)
                return True, None

        pusher = PushScheduler(SlowGit(), interval=0, clock=time.monotonic)
        pusher.mark()
        worker = threading.Thread(target=pusher.tick)
        worker.start()
        time.sleep(0.1)
        pusher.mark()
        worker.join()
        self.assertTrue(pusher.state()["pending_push"])


class DateAndUiTest(WikiCase):
    def test_absurd_years_are_rejected(self):
        root = self.make_wiki(dict(PERSON, **{"operations/tasks/T.md": md("type: task\ntitle: T")}))
        board = Board(root, today=lambda: TODAY)
        with self.assertRaises(Invalid):
            board.update({"path": "operations/tasks/T.md", "set": {"due": "0002-10-10"}})

    def test_ui_serialises_patches_and_commits_dates_on_blur(self):
        text = (ROOT / "toolkit" / "board" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function enqueue(", text)
        self.assertIn("function commitDate(", text)
        self.assertNotIn("if (el.id === 'menu-date') { var p = $('menu').dataset.path; closeMenu(); if (el.value)", text)
        self.assertIn("if (el.type === 'date') return;", text)


if __name__ == "__main__":
    unittest.main()
