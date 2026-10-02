import unittest

from helpers import WikiCase, git, md, run_cli

FILES = {
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi"),
    "knowledge/projects/Migrazione DB.md": md("type: project\ntitle: Migrazione DB"),
}


class TasksWriteCliTest(WikiCase):
    def test_add_then_update(self):
        root = self.make_git_wiki(FILES)
        code, data, _ = run_cli("tasks", "add", "--title", "Chiamare Luca", "--owner", "Luca Bianchi",
                                "--due", "2026-10-09", "--related", "Migrazione DB", "--related", "Luca Bianchi",
                                "--wiki", root, "--today", "2026-10-02")
        self.assertEqual(code, 0, data)
        self.assertEqual((data["task"]["owner"], data["committed"], data["pushed"]), ("Luca Bianchi", True, None))
        self.assertEqual(data["task"]["related"], ["Migrazione DB", "Luca Bianchi"])
        path = data["task"]["path"]

        code, data, _ = run_cli("tasks", "update", path, "--set", "priority=high", "--unset", "due",
                                "--set", "related=Migrazione DB", "--note", "fatto il punto",
                                "--wiki", root, "--today", "2026-10-02")
        self.assertEqual(code, 0, data)
        self.assertEqual((data["task"]["priority"], data["task"]["due"], data["task"]["related"]),
                         ("high", None, ["Migrazione DB"]))
        self.assertTrue(git(root, "log", "-1", "--format=%s").startswith("sb(board): Chiamare Luca → "))

    def test_errors_carry_their_payload(self):
        root = self.make_git_wiki(FILES)
        run_cli("tasks", "add", "--title", "Chiamare Luca", "--wiki", root)
        code, data, _ = run_cli("tasks", "add", "--title", "Chiamare Luca", "--wiki", root)
        self.assertEqual((code, data["path"]), (2, "operations/tasks/Chiamare Luca.md"))
        code, data, _ = run_cli("tasks", "update", "operations/tasks/Chiamare Luca.md", "--set", "status=wip",
                                "--wiki", root)
        self.assertEqual(code, 2)
        self.assertIn("stato non ammesso", data["error"])
        code, data, _ = run_cli("tasks", "update", "operations/tasks/Chiamare Luca.md", "--set", "priority",
                                "--wiki", root)
        self.assertEqual(code, 2)

    def test_add_pushes_when_a_remote_exists(self):
        root = self.make_git_wiki(FILES)
        remote = self.add_bare_remote(root)
        code, data, _ = run_cli("tasks", "add", "--title", "Con push", "--wiki", root)
        self.assertEqual((code, data["pushed"]), (0, True))
        self.assertEqual(git(remote, "rev-parse", "main").strip(), git(root, "rev-parse", "HEAD").strip())


if __name__ == "__main__":
    unittest.main()
