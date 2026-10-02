import datetime
import unittest

from helpers import WikiCase, md, run_cli
from sb_core.sources import parse_external, stale_sources
from sb_core.wiki import Wiki

TODAY = datetime.date(2026, 10, 2)


def note(title, external, extra=""):
    return md(f'type: source-note\ntitle: {title}\nexternal: "{external}"\n{extra}')


FILES = {
    "knowledge/sources/Fresca.md": note("Fresca", "confluence:ENG/1", "synced: 2026-09-20"),
    "knowledge/sources/Vecchia.md": note("Vecchia", "confluence:ENG/2", "synced: 2026-08-01"),
    "knowledge/sources/Jira.md": note("Jira", "jira:PLAT-1", "synced: 2026-09-15"),
    "knowledge/sources/Mai.md": note("Mai", "confluence:ENG/3"),
    "knowledge/sources/Migrata.md": note("Migrata", "confluence:OLD/4", "synced: 2025-01-01\nauthority: migrated"),
    "knowledge/sources/Articolo.md": note("Articolo", "url:https://example.com/a", "synced: 2025-01-01"),
    "knowledge/sources/Altro spazio.md": note("Altro spazio", "confluence:HR/9", "synced: 2026-08-25"),
}


class SourcesTest(WikiCase):
    def test_parse_external(self):
        self.assertEqual(parse_external("confluence:ENG/123"), ("confluence", "ENG"))
        self.assertEqual(parse_external("jira:PLAT-123"), ("jira", "PLAT"))
        self.assertEqual(parse_external("mail:"), ("mail", None))

    def test_stale_sources(self):
        items = stale_sources(Wiki(self.make_wiki(FILES)), TODAY)
        self.assertEqual([i["title"] for i in items], ["Mai", "Vecchia", "Altro spazio", "Jira"])
        by_title = {i["title"]: i for i in items}
        self.assertEqual(by_title["Mai"]["reason"], "never-synced")
        self.assertIsNone(by_title["Mai"]["age_days"])
        self.assertEqual((by_title["Vecchia"]["age_days"], by_title["Vecchia"]["source_id"]), (62, "conf-eng"))
        self.assertEqual((by_title["Jira"]["source_id"], by_title["Jira"]["threshold_days"]), ("jira-plat", 14))
        self.assertEqual((by_title["Altro spazio"]["source_id"], by_title["Altro spazio"]["threshold_days"]), (None, 30))
        self.assertEqual(by_title["Vecchia"]["external"], "confluence:ENG/2")
        self.assertEqual(by_title["Vecchia"]["synced"], "2026-08-01")

    def test_cli(self):
        code, data, _ = run_cli("sources", "stale", "--today", "2026-10-02", "--wiki", self.make_wiki(FILES))
        self.assertEqual((code, len(data["stale"])), (0, 4))


if __name__ == "__main__":
    unittest.main()
