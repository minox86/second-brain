import json
import unittest

from helpers import WikiCase, run_cli

EVENT = {
    "id": "EV1", "subject": "Review: Roadmap 27",
    "organizer": {"name": "Andrea B", "address": "a@example.com"},
    "attendees": [{"name": "Andrea B", "address": "a@example.com"}],
    "start": {"dateTime": "2026-10-02T07:00:00.0000000", "timeZone": "UTC"},
    "end": {"dateTime": "2026-10-02T07:40:00.0000000", "timeZone": "UTC"},
}
VTT = "WEBVTT\r\n\r\n00:00:01.000 --> 00:00:02.000\r\n<v Andrea B>Ciao.</v>"


class MeetingCliTest(WikiCase):
    def setUp(self):
        self.root = self.make_wiki()
        self.tmp = self.root / ".sb" / "tmp"
        self.tmp.mkdir(parents=True)

    def write(self, name, data, binary=False):
        path = self.tmp / name
        if binary:
            path.write_bytes(data)
        else:
            path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return path

    def capture(self, *extra):
        return run_cli("meeting", "capture", "--wiki", self.root, "--today", "2026-10-04",
                       "--event", self.write("event.json", EVENT), *extra)

    def test_capture_with_mcp_transcript(self):
        transcript = self.write("t.json", {"transcripts": [{"content": VTT}]})
        chat = self.write("chat.json", [{"messageType": "message", "from": "Andrea B",
                                         "createdDateTime": "2026-10-02T07:05:00Z", "bodyPreview": "ok"}])
        code, data, err = self.capture("--transcript", transcript, "--chat", chat)
        self.assertEqual(code, 0, err)
        self.assertEqual(data, {"ok": True, "path": "raw/2026/10/2026-10-02-review-roadmap-27.md",
                                "kind": "transcript"})
        text = (self.root / data["path"]).read_text(encoding="utf-8")
        self.assertIn("origin: teams:event/EV1", text)
        self.assertIn("- 07:05 Andrea B: ok", text)

    def test_capture_preserves_transcript_bytes(self):
        transcript = self.write("t.vtt", VTT.encode("utf-8"), binary=True)
        code, data, err = self.capture("--transcript", transcript)
        self.assertEqual(code, 0, err)
        raw = (self.root / data["path"]).read_bytes()
        self.assertTrue(raw.endswith(VTT.encode("utf-8")))
        self.assertIn(b"\r\n<v Andrea B>", raw)

    def test_capture_with_dictation_only(self):
        code, data, err = self.capture("--dictation", self.write("d.txt", "Deciso di rinviare."))
        self.assertEqual(code, 0, err)
        self.assertEqual(data["kind"], "dictation")
        text = (self.root / data["path"]).read_text(encoding="utf-8")
        self.assertIn("## Dettato\nDeciso di rinviare.", text)
        self.assertIn("_Chat non disponibile._", text)

    def test_capture_twice_is_rejected(self):
        dictation = self.write("d.txt", "x")
        self.assertEqual(self.capture("--dictation", dictation)[0], 0)
        code, data, _ = self.capture("--dictation", dictation)
        self.assertEqual(code, 1)
        self.assertEqual(data, {"ok": False, "error": "already-captured",
                                "path": "raw/2026/10/2026-10-02-review-roadmap-27.md"})

    def test_capture_needs_transcript_or_dictation(self):
        empty = self.write("t.json", {"transcripts": []})
        code, data, _ = self.capture("--transcript", empty)
        self.assertEqual(code, 2)
        self.assertIn("--dictation", data["error"])

    def test_capture_malformed_transcript_json_is_usage_error(self):
        for content in ('{"transcripts": [', '{"transcripts": "abc"}'):
            with self.subTest(content=content):
                code, data, err = self.capture("--transcript", self.write("t.json", content))
                self.assertEqual(code, 2)
                self.assertIn("trascrizione", data["error"])
                self.assertNotIn("errore interno", data["error"])

    def test_capture_rejects_transcript_that_is_not_webvtt(self):
        wrapped = json.dumps([{"type": "text", "text": json.dumps({"transcripts": [{"content": VTT}]})}])
        for content in (wrapped, "Error: resource not found"):
            with self.subTest(content=content[:20]):
                code, data, _ = self.capture("--transcript", self.write("t.txt", content))
                self.assertEqual(code, 2)
                self.assertIn("trascrizione", data["error"])
        self.assertFalse((self.root / "raw").exists())

    def test_capture_bad_event(self):
        bad = self.write("bad.json", "{non json")
        code, data, _ = run_cli("meeting", "capture", "--wiki", self.root, "--event", bad,
                                "--dictation", self.write("d.txt", "x"))
        self.assertEqual(code, 2)
        self.assertIn("evento", data["error"])
        nostart = self.write("e2.json", {"id": "X"})
        code, _, _ = run_cli("meeting", "capture", "--wiki", self.root, "--event", nostart,
                             "--dictation", self.write("d.txt", "x"))
        self.assertEqual(code, 2)

    def test_capture_bad_chat(self):
        chat = self.write("chat.json", {"not": "a list"})
        code, data, _ = self.capture("--dictation", self.write("d.txt", "x"), "--chat", chat)
        self.assertEqual(code, 2)
        self.assertIn("chat", data["error"])

    def test_seen(self):
        self.capture("--dictation", self.write("d.txt", "x"))
        code, data, _ = run_cli("meeting", "seen", "EV1", "EV2", "--wiki", self.root)
        self.assertEqual(code, 0)
        self.assertEqual(data, {"seen": {"EV1": "raw/2026/10/2026-10-02-review-roadmap-27.md"}})


if __name__ == "__main__":
    unittest.main()
