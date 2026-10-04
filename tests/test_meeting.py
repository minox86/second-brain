import json
import unittest

from helpers import ROOT  # noqa: F401  (aggiunge toolkit/ al path)

from sb_core.meeting import (agenda_text, attendance, chat_lines, format_duration, html_to_text,
                             transcript_text)

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


if __name__ == "__main__":
    unittest.main()
