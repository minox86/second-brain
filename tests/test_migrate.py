import json
import unittest

from helpers import WikiCase, md, run_cli
from sb_core.errors import PlanError
from sb_core.frontmatter import parse
from sb_core.migrate import migrate
from sb_core.validate import validate
from sb_core.wiki import Wiki

TASK = "operations/tasks/Chiamare Acme.md"
FILES = {
    "knowledge/topics/Acme.md": md("type: topic\ntitle: Acme", "Fornitore storico.\n"),
    "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi\nrole: EM"),
    TASK: md(
        'type: task\ntitle: Chiamare Acme\nowner: "[[Luca Bianchi]]"\nrelated: ["[[Acme]]"]',
        "Parlare con [[Luca Bianchi|Luca]] di [[Acme#contratto]].\n",
    ),
}


class MigrateTest(WikiCase):
    def setUp(self):
        self.root = self.make_wiki(FILES)

    def meta(self, rel):
        return parse((self.root / rel).read_text(encoding="utf-8"))

    def test_move_and_retype(self):
        result = migrate(Wiki(self.root), [
            {"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/vendors/Acme.md", "set": {"type": "vendor"}},
        ])
        self.assertFalse((self.root / "knowledge/topics/Acme.md").exists())
        meta, body = self.meta("knowledge/vendors/Acme.md")
        self.assertEqual((meta["type"], body), ("vendor", "Fornitore storico.\n"))
        self.assertEqual(result["changes"], [{"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/vendors/Acme.md"}])
        self.assertEqual([i.code for i in validate(Wiki(self.root)) if i.severity == "error"], [])

    def test_pure_move_keeps_bytes(self):
        before = (self.root / "knowledge/topics/Acme.md").read_bytes()
        migrate(Wiki(self.root), [{"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/topics/sub/Acme.md"}])
        self.assertEqual((self.root / "knowledge/topics/sub/Acme.md").read_bytes(), before)

    def test_retitle_rewrites_links(self):
        result = migrate(Wiki(self.root), [
            {"op": "retitle", "path": "knowledge/people/Luca Bianchi.md", "title": "Luca Bianchi Rossi"},
        ])
        self.assertFalse((self.root / "knowledge/people/Luca Bianchi.md").exists())
        meta, _ = self.meta("knowledge/people/Luca Bianchi Rossi.md")
        self.assertEqual((meta["title"], meta["aliases"]), ("Luca Bianchi Rossi", ["Luca Bianchi"]))
        task_meta, task_body = self.meta(TASK)
        self.assertEqual(task_meta["owner"], "[[Luca Bianchi Rossi]]")
        self.assertEqual(task_body, "Parlare con [[Luca Bianchi Rossi|Luca]] di [[Acme#contratto]].\n")
        self.assertEqual(result["changes"][0]["links_rewritten"], 2)
        self.assertEqual(validate(Wiki(self.root)), [])

    def test_rename_field_touches_only_matching_pages(self):
        task_before = (self.root / TASK).read_text(encoding="utf-8")
        migrate(Wiki(self.root), [{"op": "rename_field", "type": "person", "from": "role", "to": "position"}])
        meta, _ = self.meta("knowledge/people/Luca Bianchi.md")
        self.assertEqual(list(meta), ["type", "title", "position"])
        self.assertEqual((self.root / TASK).read_text(encoding="utf-8"), task_before)

    def test_set_and_remove_fields(self):
        migrate(Wiki(self.root), [{"op": "set", "path": TASK, "fields": {"priority": "high", "owner": None}}])
        meta, _ = self.meta(TASK)
        self.assertEqual(meta["priority"], "high")
        self.assertNotIn("owner", meta)

    def test_dry_run_writes_nothing(self):
        result = migrate(Wiki(self.root), [{"op": "set", "path": TASK, "fields": {"priority": "high"}}], dry_run=True)
        self.assertEqual((result["dry_run"], result["written"], len(result["changes"])), (True, [], 1))
        self.assertNotIn("priority", self.meta(TASK)[0])

    def test_errors_leave_wiki_untouched(self):
        plans = [
            [{"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/vendors/Acme.md"},
             {"op": "move", "path": "knowledge/topics/Nessuno.md", "to": "knowledge/vendors/Nessuno.md"}],
            [{"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/people/Luca Bianchi.md"}],
            [{"op": "retitle", "path": TASK, "title": "Titolo: non valido"}],
            [{"op": "explode"}],
            [{"op": "move", "path": "knowledge/topics/Acme.md", "to": "../fuori.md"}],
        ]
        for ops in plans:
            with self.subTest(ops=ops):
                with self.assertRaises(PlanError):
                    migrate(Wiki(self.root), ops)
                self.assertTrue((self.root / "knowledge/topics/Acme.md").exists())

    def test_cli(self):
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"ops": [{"op": "set", "path": TASK, "fields": {"priority": "low"}}]}), encoding="utf-8")
        code, data, _ = run_cli("migrate", plan, "--dry-run", "--wiki", self.root)
        self.assertEqual((code, data["dry_run"]), (0, True))
        code, data, _ = run_cli("migrate", plan, "--wiki", self.root)
        self.assertEqual((code, data["written"]), (0, [TASK]))
        plan.write_text('{"ops": []}', encoding="utf-8")
        self.assertEqual(run_cli("migrate", plan, "--wiki", self.root)[0], 2)


if __name__ == "__main__":
    unittest.main()
