"""Regressioni emerse dalla revisione finale del branch."""
import datetime
import os
import unicodedata
import unittest

from helpers import ROOT, WikiCase, md, run_cli
from sb_core.errors import PlanError
from sb_core.frontmatter import parse
from sb_core.migrate import migrate
from sb_core.status import status
from sb_core.tasks import list_tasks
from sb_core.validate import validate
from sb_core.wiki import Wiki

TODAY = datetime.date(2026, 10, 2)


class MigrateSafetyTest(WikiCase):
    def test_case_only_collision_between_destinations_is_refused(self):
        root = self.make_wiki({
            "knowledge/topics/Hiring.md": md("type: topic\ntitle: Hiring"),
            "knowledge/topics/Budget.md": md("type: topic\ntitle: Budget"),
        })
        with self.assertRaises(PlanError):
            migrate(Wiki(root), [
                {"op": "retitle", "path": "knowledge/topics/Hiring.md", "title": "Piano 2027"},
                {"op": "retitle", "path": "knowledge/topics/Budget.md", "title": "piano 2027"},
            ])
        self.assertTrue((root / "knowledge/topics/Hiring.md").exists())
        self.assertTrue((root / "knowledge/topics/Budget.md").exists())

    def test_destination_outside_page_roots_is_refused(self):
        root = self.make_wiki({"knowledge/topics/Acme.md": md("type: topic\ntitle: Acme")})
        with self.assertRaises(PlanError):
            migrate(Wiki(root), [{"op": "move", "path": "knowledge/topics/Acme.md", "to": "schema/types/Acme.md"}])

    def test_move_with_new_stem_rewrites_links(self):
        root = self.make_wiki({
            "knowledge/people/luca.md": md("type: person\ntitle: Luca Bianchi"),
            "knowledge/people/Anna.md": md("type: person\ntitle: Anna", "Lavora con [[luca|Luca]].\n"),
        })
        migrate(Wiki(root), [{"op": "move", "path": "knowledge/people/luca.md", "to": "knowledge/people/Luca Bianchi.md"}])
        self.assertIn("[[Luca Bianchi|Luca]]", (root / "knowledge/people/Anna.md").read_text(encoding="utf-8"))
        self.assertEqual(validate(Wiki(root)), [])

    def test_relink_redirects_links_after_merge(self):
        root = self.make_wiki({
            "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi"),
            "knowledge/people/Anna.md": md("type: person\ntitle: Anna", "Vedi [[Luca B#Note]].\n"),
        })
        result = migrate(Wiki(root), [{"op": "relink", "from": "Luca B", "to": "Luca Bianchi"}])
        self.assertIn("[[Luca Bianchi#Note]]", (root / "knowledge/people/Anna.md").read_text(encoding="utf-8"))
        self.assertEqual(result["changes"][0]["links_rewritten"], 1)

    def test_retitle_rewrites_links_in_pages_without_valid_frontmatter(self):
        root = self.make_wiki({
            "knowledge/people/Luca.md": md("type: person\ntitle: Luca"),
            "knowledge/topics/Appunti.md": "Note libere su [[Luca]].\n",
        })
        migrate(Wiki(root), [{"op": "retitle", "path": "knowledge/people/Luca.md", "title": "Luca Bianchi"}])
        self.assertEqual((root / "knowledge/topics/Appunti.md").read_text(encoding="utf-8"),
                         "Note libere su [[Luca Bianchi]].\n")

    def test_non_string_path_is_a_plan_error(self):
        root = self.make_wiki()
        with self.assertRaises(PlanError):
            migrate(Wiki(root), [{"op": "set", "path": ["x"], "fields": {"a": 1}}])


class RobustnessTest(WikiCase):
    def test_non_string_type_is_reported_not_crashing(self):
        root = self.make_wiki({"knowledge/people/X.md": md("type: [person]\ntitle: X")})
        codes = [i.code for i in validate(Wiki(root))]
        self.assertIn("bad-value", codes)
        for cmd in ("index", "lint", "status"):
            with self.subTest(cmd=cmd):
                code, data, _ = run_cli(cmd, "--wiki", root)
                self.assertIn(code, (0, 1))
                self.assertIsNotNone(data)

    def test_unexpected_exception_exits_2_with_json(self):
        from unittest import mock

        root = self.make_wiki()
        with mock.patch("sb_core.cli.write_index", side_effect=RuntimeError("boom")):
            code, data, err = run_cli("index", "--wiki", root)
        self.assertEqual(code, 2)
        self.assertIn("boom", data["error"])

    def test_unindented_block_list(self):
        meta, _ = parse("---\ntitle: Luca\naliases:\n- Luca\n- LB\nrole: EM\n---\n")
        self.assertEqual(meta, {"title": "Luca", "aliases": ["Luca", "LB"], "role": "EM"})

    def test_attachments_and_code_are_not_broken_links(self):
        root = self.make_wiki({
            "knowledge/topics/T.md": md(
                "type: topic\ntitle: T",
                "![[Pasted image 20261002.png]] e [[budget.pdf]]\n\n```\n[[Nel codice]]\n```\n"
                "Inline `[[Anche questo]]` ma [[Fantasma]] no.\n",
            ),
        })
        issues = [(i.code, i.message) for i in validate(Wiki(root))]
        self.assertEqual([c for c, _ in issues], ["broken-link"])
        self.assertIn("Fantasma", issues[0][1])

    def test_nfd_filenames_match_nfc_links(self):
        nfd = unicodedata.normalize("NFD", "Nicolò Rossi")
        root = self.make_wiki({
            f"knowledge/people/{nfd}.md": md("type: person\ntitle: Nicolò Rossi"),
            "knowledge/people/Anna.md": md("type: person\ntitle: Anna", "Con [[Nicolò Rossi]].\n"),
        })
        self.assertEqual(validate(Wiki(root)), [])

    def test_validate_relative_path_from_subfolder(self):
        root = self.make_wiki({"knowledge/people/Marco.md": md("type: person\ntitle: Marco")})
        cwd = os.getcwd()
        os.chdir(root / "knowledge" / "people")
        self.addCleanup(os.chdir, cwd)
        code, data, _ = run_cli("validate", "Marco.md")
        self.assertEqual((code, data["checked"]), (0, 1))


class ResolvedNamesTest(WikiCase):
    FILES = {
        "knowledge/people/Luca Bianchi.md": md("type: person\ntitle: Luca Bianchi\naliases: [Luca]"),
        "knowledge/people/Ex Collega.md": md("type: person\ntitle: Ex Collega\nstatus: left"),
        "operations/one-on-ones/2026-08-01 1on1 Luca.md": md(
            'type: one-on-one\ntitle: 2026-08-01 1on1 Luca\nwith: "[[Luca]]"\ndate: 2026-08-01'),
        "operations/one-on-ones/2026-09-30 1on1 Luca.md": md(
            'type: one-on-one\ntitle: 2026-09-30 1on1 Luca\nwith: "[[Luca Bianchi]]"\ndate: 2026-09-30'),
        "operations/one-on-ones/2026-05-01 1on1 Ex.md": md(
            'type: one-on-one\ntitle: 2026-05-01 1on1 Ex\nwith: "[[Ex Collega]]"\ndate: 2026-05-01'),
        "operations/tasks/Stima.md": md('type: task\ntitle: Stima\nowner: "[[Luca]]"'),
    }

    def test_one_on_one_gaps_resolve_aliases_and_skip_people_who_left(self):
        self.assertEqual(status(Wiki(self.make_wiki(self.FILES)), TODAY)["one_on_one_gaps"], [])

    def test_person_filter_resolves_aliases(self):
        wiki = Wiki(self.make_wiki(self.FILES))
        self.assertEqual([t["title"] for t in list_tasks(wiki, view="all", person="Luca Bianchi", today=TODAY)],
                         ["Stima"])


class SkillTextTest(unittest.TestCase):
    def test_sync_grep_tolerates_unquoted_external(self):
        text = (ROOT / "skills" / "sync" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn('grep -rlE \'external: "?', text)

    def test_lint_uses_retitle_for_filename_mismatch_and_relink_for_merges(self):
        text = (ROOT / "skills" / "lint" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`filename-mismatch`: operazione `retitle`", text)
        self.assertIn("`relink`", text)


if __name__ == "__main__":
    unittest.main()
