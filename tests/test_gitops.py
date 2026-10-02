import os
import unittest

from helpers import WikiCase, git, md
from sb_core.gitops import Git, PushScheduler

A = "operations/tasks/A.md"


class GitTest(WikiCase):
    def test_commits_only_the_given_paths(self):
        root = self.make_git_wiki({A: md("type: task\ntitle: A")})
        (root / A).write_text(md("type: task\ntitle: A\nstatus: done"), encoding="utf-8")
        (root / "operations/tasks/B.md").write_text(md("type: task\ntitle: B"), encoding="utf-8")
        (root / "knowledge/topics").mkdir(parents=True)
        (root / "knowledge/topics/Estraneo.md").write_text(md("type: topic\ntitle: Estraneo"), encoding="utf-8")
        ok, error = Git(root).commit([A, "operations/tasks/B.md", "operations/tasks/Mancante.md"], "sb(board): test")
        self.assertEqual((ok, error), (True, None))
        committed = git(root, "show", "--name-only", "--format=", "HEAD").split("\n")
        self.assertEqual(sorted(p for p in committed if p), [A, "operations/tasks/B.md"])
        self.assertIn("knowledge/", git(root, "status", "--porcelain"))
        self.assertEqual(git(root, "log", "-1", "--format=%s").strip(), "sb(board): test")

    def test_commits_deletions(self):
        root = self.make_git_wiki({A: md("type: task\ntitle: A")})
        os.rename(str(root / A), str(root / "operations/tasks/C.md"))
        ok, _ = Git(root).commit([A, "operations/tasks/C.md"], "rename")
        self.assertTrue(ok)
        self.assertEqual(git(root, "status", "--porcelain").strip(), "")

    def test_nothing_to_commit_is_ok(self):
        root = self.make_git_wiki({A: md("type: task\ntitle: A")})
        self.assertEqual(Git(root).commit([A], "noop"), (True, None))
        self.assertEqual(git(root, "log", "-1", "--format=%s").strip(), "init")

    def test_not_a_repo(self):
        repo = Git(self.make_wiki())
        self.assertFalse(repo.is_repo())
        self.assertIsNone(repo.head())
        ok, error = repo.commit(["x.md"], "m")
        self.assertFalse(ok)
        self.assertTrue(error)

    def test_head_and_remote(self):
        root = self.make_git_wiki()
        repo = Git(root)
        self.assertTrue(repo.head())
        self.assertFalse(repo.has_remote())
        self.add_bare_remote(root)
        self.assertTrue(repo.has_remote())


class PushSchedulerTest(WikiCase):
    def test_pushes_at_most_once_per_interval_and_flushes(self):
        root = self.make_git_wiki({A: md("type: task\ntitle: A")})
        remote = self.add_bare_remote(root)
        clock = [100.0]
        pusher = PushScheduler(Git(root), interval=60, clock=lambda: clock[0])
        pusher.tick()
        self.assertFalse(pusher.state()["pending_push"])
        pusher.mark()
        pusher.tick()
        self.assertEqual(git(remote, "rev-parse", "main").strip(), git(root, "rev-parse", "HEAD").strip())
        self.assertFalse(pusher.state()["pending_push"])
        self.assertTrue(pusher.state()["last_push"])

        (root / A).write_text(md("type: task\ntitle: A\nstatus: done"), encoding="utf-8")
        Git(root).commit([A], "seconda")
        pusher.mark()
        clock[0] = 130.0
        pusher.tick()
        self.assertTrue(pusher.state()["pending_push"])
        clock[0] = 161.0
        pusher.tick()
        self.assertFalse(pusher.state()["pending_push"])
        self.assertEqual(git(remote, "rev-parse", "main").strip(), git(root, "rev-parse", "HEAD").strip())

        pusher.mark()
        clock[0] = 162.0
        pusher.flush()
        self.assertFalse(pusher.state()["pending_push"])

    def test_failed_push_stays_pending(self):
        root = self.make_git_wiki()
        git(root, "remote", "add", "origin", "/percorso/che/non/esiste.git")
        pusher = PushScheduler(Git(root), clock=lambda: 0.0)
        pusher.mark()
        pusher.tick()
        state = pusher.state()
        self.assertTrue(state["pending_push"])
        self.assertTrue(state["last_error"])

    def test_without_remote_nothing_stays_pending(self):
        pusher = PushScheduler(Git(self.make_git_wiki()), clock=lambda: 0.0)
        pusher.mark()
        pusher.flush()
        self.assertFalse(pusher.state()["pending_push"])


if __name__ == "__main__":
    unittest.main()
