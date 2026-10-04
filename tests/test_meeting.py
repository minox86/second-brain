import datetime
import json
import unittest

from helpers import ROOT, WikiCase  # noqa: F401  (aggiunge toolkit/ al path)

from sb_core.frontmatter import parse
from sb_core.meeting import (agenda_text, attendance, chat_lines, event_date, format_duration, html_to_text,
                             origin_for, raw_path_for, render_raw, seen, slug_for, transcript_text)

TEAMS_BLOCK = (
    "<div>________________________________________________________________________________</div>"
    "<div><b>Riunione di Microsoft Teams</b></div>"
    "<div>Partecipa a: <a href=\"https://teams.microsoft.com/meet/1\">https://teams.microsoft.com/meet/1</a></div>"
)


def system(kind, **detail):
    detail["@odata.type"] = "#microsoft.graph." + kind
    return {"messageType": "unknownFutureValue", "eventDetail": detail, "from": "Unknown",
            "createdDateTime": "2026-09-30T11:00:00Z", "bodyPreview": "<systemEventMessage/>"}


def user(name):
    return {"participant": {"user": {"displayName": name}, "application": None, "device": None}}


BOT = {"participant": {"user": None, "application": {"displayName": ""}, "device": None}}


class HtmlTest(unittest.TestCase):
    def test_html_to_text_blocks_links_entities(self):
        html = "<p>Ciao&nbsp;a tutti</p><p>vedi <a href=\"https://x.io/a\">il doc</a></p><br>fine"
        self.assertEqual(html_to_text(html), "Ciao a tutti\nvedi il doc (https://x.io/a)\nfine")

    def test_html_to_text_link_equal_to_text_not_repeated(self):
        html = "<a href=\"https://x.io\">https://x.io</a>"
        self.assertEqual(html_to_text(html), "https://x.io")

    def test_html_to_text_ignores_style_and_empty(self):
        self.assertEqual(html_to_text("<style>p{color:red}</style><p>ok</p>"), "ok")
        self.assertEqual(html_to_text(None), "")

    def test_agenda_keeps_organizer_text_and_drops_teams_block(self):
        html = "<div>Questo incontro serve a decidere X.</div><br>" + TEAMS_BLOCK
        self.assertEqual(agenda_text(html), "Questo incontro serve a decidere X.")

    def test_agenda_empty_when_only_teams_block(self):
        self.assertEqual(agenda_text("<p>&nbsp;</p>" + TEAMS_BLOCK), "")


class ChatTest(unittest.TestCase):
    def test_chat_lines_mixed_shapes(self):
        messages = [
            {"messageType": "message", "from": {"displayName": "Alberto Zitti"},
             "createdDateTime": "2026-09-30T10:51:55.663Z", "body": {"contentType": "html", "content": None},
             "attachments": [{"name": "metering.excalidraw", "contentUrl": "https://sp/x"}]},
            system("callEndedEventMessageDetail", callParticipants=[], callDuration="PT1H"),
            {"messageType": "message", "from": "Elisa Giorgi", "createdDateTime": "2026-09-30T10:58:30.201Z",
             "bodyPreview": "<p><a href=\"https://ghe/repo\">https://ghe/repo</a></p>"},
            {"messageType": "message", "from": {"displayName": "Luca"}, "createdDateTime": "2026-09-30T10:40:00Z",
             "body": {"content": "<p>riga uno</p><p>riga due</p>"}},
            {"messageType": "message", "from": {"displayName": "X"}, "createdDateTime": "2026-09-30T10:41:00Z",
             "deletedDateTime": "2026-09-30T10:42:00Z", "body": {"content": "<p>cancellato</p>"}},
        ]
        self.assertEqual(chat_lines(messages), [
            "10:40 Luca: riga uno riga due",
            "10:51 Alberto Zitti: [allegato: metering.excalidraw] https://sp/x",
            "10:58 Elisa Giorgi: https://ghe/repo",
        ])

    def test_chat_lines_attachment_without_name(self):
        messages = [{"messageType": "message", "from": "A", "createdDateTime": "2026-09-30T09:00:00Z",
                     "bodyPreview": "<attachment id=\"1\"></attachment>"}]
        self.assertEqual(chat_lines(messages), ["09:00 A: [allegato]"])

    def test_attendance(self):
        messages = [
            system("callEndedEventMessageDetail", callDuration="PT1H26M21S",
                   callParticipants=[user("Elisa Giorgi"), BOT, user("Alberto Zitti")]),
            system("callRecordingEventMessageDetail", callRecordingStatus="chunkFinished", callRecordingUrl=""),
            system("callRecordingEventMessageDetail", callRecordingStatus="success",
                   callRecordingUrl="https://sp/rec.mp4"),
        ]
        self.assertEqual(attendance(messages), {
            "present": ["Elisa Giorgi", "Alberto Zitti"], "duration": "1h26", "recording": "https://sp/rec.mp4"})

    def test_attendance_without_system_events(self):
        self.assertEqual(attendance([]), {})

    def test_format_duration(self):
        self.assertEqual(format_duration("PT1H26M21S"), "1h26")
        self.assertEqual(format_duration("PT2H"), "2h00")
        self.assertEqual(format_duration("PT45M10S"), "45 min")
        self.assertEqual(format_duration("PT30S"), "1 min")
        self.assertIsNone(format_duration("boh"))


VTT = "WEBVTT\r\n\r\n00:00:03.448 --> 00:00:05.248\r\n<v Alberto Zitti>Ora mi torna.</v>"


class TranscriptTest(unittest.TestCase):
    def test_transcript_text_from_mcp_payload(self):
        payload = {"meeting": {}, "transcripts": [
            {"createdDateTime": "2026-09-30T10:00:00Z", "content": "WEBVTT\n\nB"},
            {"createdDateTime": "2026-09-30T09:00:00Z", "content": VTT},
            {"createdDateTime": "2026-09-30T11:00:00Z", "content": ""},
        ]}
        self.assertEqual(transcript_text(payload), VTT + "\n\n" + "WEBVTT\n\nB")

    def test_transcript_text_empty(self):
        self.assertIsNone(transcript_text({"transcripts": []}))
        self.assertIsNone(transcript_text(None))
        self.assertIsNone(transcript_text("   "))

    def test_transcript_text_accepts_plain_vtt(self):
        self.assertEqual(transcript_text(VTT), VTT)

    def test_transcript_text_accepts_json_string(self):
        self.assertEqual(transcript_text(json.dumps({"transcripts": [{"content": VTT}]})), VTT)


EVENT = {
    "id": "AAkALgAAA-EbQAA=",
    "subject": "TouchX - Metering: come capiamo quando un'offerta è attiva?",
    "body": {"contentType": "html", "content": "<div>Serve a decidere X.</div>" + TEAMS_BLOCK},
    "organizer": {"name": "Emanuele Fabbiani", "address": "e.f@example.com"},
    "attendees": [{"name": "Emanuele Fabbiani", "address": "e.f@example.com"},
                  {"name": "Alberto Zitti", "address": "a.z@example.com"},
                  {"name": "Mattia Minotti", "address": "m.m@example.com"}],
    "start": {"dateTime": "2026-09-30T09:30:00.0000000", "timeZone": "UTC"},
    "end": {"dateTime": "2026-09-30T10:00:00.0000000", "timeZone": "UTC"},
}
TODAY = datetime.date(2026, 10, 4)


class SlugTest(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(slug_for(EVENT["subject"]), "touchx-metering-come-capiamo-quando-un-offerta-e-attiva")
        self.assertEqual(slug_for("Annullata: Weekly Platform"), "weekly-platform")
        self.assertEqual(slug_for("Canceled: Sync"), "sync")
        self.assertEqual(slug_for("???"), "riunione")
        self.assertEqual(slug_for(None), "riunione")
        long = slug_for("parola " * 30)
        self.assertLessEqual(len(long), 60)
        self.assertFalse(long.endswith("-"))

    def test_event_date_and_origin(self):
        self.assertEqual(event_date(EVENT), "2026-09-30")
        self.assertEqual(origin_for(EVENT), "teams:event/AAkALgAAA-EbQAA=")


class RawPathTest(WikiCase):
    def test_path_and_collision(self):
        root = self.make_wiki()
        first = raw_path_for(root, EVENT)
        self.assertEqual(first.relative_to(root).as_posix(),
                         "raw/2026/09/2026-09-30-touchx-metering-come-capiamo-quando-un-offerta-e-attiva.md")
        first.parent.mkdir(parents=True)
        first.write_text("x", encoding="utf-8")
        second = raw_path_for(root, EVENT)
        self.assertTrue(second.name.endswith("-attiva-2.md"))


class RenderTest(unittest.TestCase):
    CHAT = [
        {"messageType": "message", "from": "Elisa Giorgi", "createdDateTime": "2026-09-30T10:58:30Z",
         "bodyPreview": "<p>https://ghe/repo</p>"},
        {"messageType": "unknownFutureValue", "from": "Unknown", "createdDateTime": "2026-09-30T11:01:53Z",
         "eventDetail": {"@odata.type": "#microsoft.graph.callEndedEventMessageDetail", "callDuration": "PT1H26M21S",
                         "callParticipants": [user("Elisa Giorgi"), user("Alberto Zitti")]}},
    ]

    def test_full_render(self):
        vtt = "WEBVTT\r\n\r\n00:00:03.448 --> 00:00:05.248\r\n<v Alberto Zitti>Ora mi torna.</v>\r\n"
        text = render_raw(EVENT, vtt, self.CHAT, None, TODAY)
        meta, body = parse(text)
        self.assertEqual(meta, {"kind": "transcript", "captured": "2026-10-04",
                                "origin": "teams:event/AAkALgAAA-EbQAA=", "meeting_date": "2026-09-30"})
        self.assertIn("# TouchX - Metering: come capiamo quando un'offerta è attiva?\n", body)
        self.assertIn("- Orario: 2026-09-30 09:30–10:00 UTC · durata effettiva 1h26\n", body)
        self.assertIn("- Organizzatore: Emanuele Fabbiani\n", body)
        self.assertIn("- Invitati: Emanuele Fabbiani, Alberto Zitti, Mattia Minotti\n", body)
        self.assertIn("- Presenti: Elisa Giorgi, Alberto Zitti\n", body)
        self.assertIn("Agenda:\nServe a decidere X.\n", body)
        self.assertIn("## Chat (orari UTC)\n- 10:58 Elisa Giorgi: https://ghe/repo\n", body)
        self.assertNotIn("Registrazione", body)
        self.assertTrue(text.endswith("## Trascrizione\n" + vtt))

    def test_dictation_render_and_missing_chat(self):
        text = render_raw(EVENT, None, None, "  Abbiamo deciso Y.\n", TODAY)
        meta, body = parse(text)
        self.assertEqual(meta["kind"], "dictation")
        self.assertIn("## Chat\n_Chat non disponibile._\n", body)
        self.assertIn("## Dettato\nAbbiamo deciso Y.\n", body)
        self.assertNotIn("## Trascrizione", body)

    def test_empty_chat_section_is_omitted(self):
        text = render_raw(EVENT, "WEBVTT\n", [], None, TODAY)
        self.assertNotIn("## Chat", text)

    def test_render_handles_search_shaped_event(self):
        event = dict(EVENT, organizer="e.f@example.com", attendees=["e.f@example.com", "a.z@example.com"],
                     body=None)
        body = parse(render_raw(event, "WEBVTT\n", [], None, TODAY))[1]
        self.assertIn("- Organizzatore: e.f@example.com\n", body)
        self.assertIn("- Invitati: e.f@example.com, a.z@example.com\n", body)
        self.assertNotIn("Agenda:", body)


class SeenTest(WikiCase):
    def test_seen(self):
        root = self.make_wiki({
            "raw/2026/09/a.md": "---\nkind: transcript\norigin: teams:event/ID1\n---\nx",
            "raw/2026/09/b.md": "---\nkind: dictation\norigin: chat\n---\nx",
        })
        self.assertEqual(seen(root, ["ID1", "ID2"]), {"ID1": "raw/2026/09/a.md"})
        self.assertEqual(seen(root, []), {})

    def test_seen_skips_broken_files(self):
        root = self.make_wiki({"raw/2026/09/rotto.md": "---\norigin: teams:event/ID1\n"})
        (root / "raw/2026/09/bin.md").write_bytes(b"\xff\xfe\x00")
        self.assertEqual(seen(root, ["ID1"]), {})

    def test_seen_ignores_non_string_origin(self):
        root = self.make_wiki({
            "raw/2026/09/lista.md": "---\norigin: [a, b]\n---\nx",
            "raw/2026/09/a.md": "---\norigin: teams:event/ID1\n---\nx",
        })
        self.assertEqual(seen(root, ["ID1"]), {"ID1": "raw/2026/09/a.md"})

    def test_seen_without_raw_folder(self):
        self.assertEqual(seen(self.make_wiki(), ["ID1"]), {})


if __name__ == "__main__":
    unittest.main()
