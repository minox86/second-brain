# Meeting Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere `/sb:meeting`, che trova riunioni Teams nel calendario via Microsoft 365, ne cattura evento, trascrizione e chat in `raw/` con un comando deterministico del toolkit e le fa analizzare dalla pipeline di `put`.

**Architecture:** La skill (`skills/meeting/SKILL.md`) gestisce risoluzione, lista del giorno e chiamate MCP, salvando le risposte in `.sb/tmp/`. Il toolkit (`toolkit/sb_core/meeting.py` + CLI `sb meeting capture|seen`) trasforma quei file nel grezzo in `raw/` e risponde alle domande di idempotenza. L'analisi riusa i passi 3–7 di `skills/put/SKILL.md`.

**Tech Stack:** Python 3.9+ solo stdlib (`html.parser`, `json`, `re`, `unicodedata`), `unittest`; skill in Markdown per Claude Code.

**Spec:** `docs/superpowers/specs/2026-10-04-meeting-ingest-design.md`

## Global Constraints

- Python ≥ 3.9, nessuna dipendenza esterna.
- Ogni comando del toolkit stampa JSON su stdout; exit `0` ok, `1` problema descritto nel JSON, `2` errore d'uso (`UsageError`).
- La trascrizione nel raw è **byte per byte** identica al `content` ricevuto (niente conversione di `\r\n`).
- `origin` del raw = `teams:event/<eventId>`; è la chiave di idempotenza.
- Percorso del raw: `raw/AAAA/MM/AAAA-MM-GG-<slug>.md`, data = data di inizio dell'evento; collisione → `-2`, `-3`…
- `meeting capture` non fa commit: lo fa il flusso di chiusura della skill.
- Le skill usano blocchi indentati, mai recinti ``` (test di layout).
- Testi utente e messaggi in italiano, come il resto del plugin.
- Stagia solo i file del task. Il working tree può contenere modifiche altrui (board): non includerle nei commit. Se un file da modificare ha già modifiche non tue, fermati e chiedi.
- Comando di test: `python3 -m unittest discover -s tests` dalla radice del repo (baseline: 206 test OK).

## Review Focus

1. **Trascrizione con `\r\n` o senza newline finale** → il raw deve contenerla identica; `read_text` di default converte i newline. Test in Task 3 (`test_capture_preserves_transcript_bytes`).
2. **Transcript passato come VTT puro invece che come JSON MCP** (la skill lo salva a mano quando arriva inline) → va accettato. Test in Task 1 (`test_transcript_text_accepts_plain_vtt`).
3. **Evento nel formato "ricerca"** (organizer e attendees come stringhe email, non dict) → il rendering non deve rompersi. Test in Task 2 (`test_render_handles_search_shaped_event`).
4. **Messaggi di chat nel formato lista** (`from` stringa, solo `bodyPreview`) mescolati a quelli letti per intero (`from` dict, `body.content` null con allegati) → righe corrette per entrambi. Test in Task 1 (`test_chat_lines_mixed_shapes`).
5. **Raw con frontmatter malformato in `raw/`** → `seen` lo salta senza fallire. Test in Task 2 (`test_seen_skips_broken_files`).

---

### Task 1: Estrazione dal materiale Teams (`meeting.py`, parte testuale)

**Files:**
- Create: `toolkit/sb_core/meeting.py`
- Create: `tests/test_meeting.py`

**Interfaces:**
- Consumes: niente.
- Produces (in `sb_core.meeting`):
  - `html_to_text(html: str | None) -> str`
  - `agenda_text(html: str | None) -> str`
  - `chat_lines(messages: list[dict]) -> list[str]` — righe `HH:MM Nome: testo` (orari UTC)
  - `attendance(messages: list[dict]) -> dict` — chiavi opzionali `present: list[str]`, `duration: str` (es. `"1h26"`), `recording: str`
  - `format_duration(iso: str) -> str | None`
  - `transcript_text(payload: dict | str | None) -> str | None`

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_meeting.py`:

```python
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
        import json
        self.assertEqual(transcript_text(json.dumps({"transcripts": [{"content": VTT}]})), VTT)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Verifica che falliscano**

Run: `cd tests && python3 -m unittest test_meeting -v`
Expected: errore di import `No module named 'sb_core.meeting'`.

- [ ] **Step 3: Implementa**

`toolkit/sb_core/meeting.py`:

```python
"""Riunioni Teams: dal materiale scaricato via Microsoft 365 al grezzo in raw/."""
import json
import re
from html.parser import HTMLParser

_BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "hr"}
_SKIP_TAGS = {"style", "script", "head", "title"}
_RULE = re.compile(r"^_{10,}$")
_DURATION = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$")


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0
        self._link = None  # (href, indice in parts dove inizia il testo del link)

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")
        elif tag == "a":
            self._link = (dict(attrs).get("href"), len(self.parts))

    def handle_startendtag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")
        elif tag == "a" and self._link:
            href, start = self._link
            self._link = None
            text = "".join(self.parts[start:]).strip()
            if href and href != text:
                self.parts.append(f" ({href})")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html):
    """Testo leggibile da un frammento HTML: blocchi su righe, link come 'testo (url)'."""
    if not html:
        return ""
    parser = _TextParser()
    parser.feed(html)
    parser.close()
    lines = (" ".join(line.split()) for line in "".join(parser.parts).split("\n"))
    return "\n".join(line for line in lines if line)


def agenda_text(html):
    """Testo dell'invito scritto dall'organizzatore, senza il blocco Teams in fondo."""
    lines = html_to_text(html).split("\n")
    for i, line in enumerate(lines):
        if _RULE.match(line):
            lines = lines[:i]
            break
    return "\n".join(lines).strip()


def _sender(message):
    sender = message.get("from")
    if isinstance(sender, dict):
        return sender.get("displayName") or (sender.get("user") or {}).get("displayName") or "?"
    return sender or "?"


def chat_lines(messages):
    """Righe 'HH:MM Nome: testo' dei soli messaggi veri, in ordine cronologico (orari UTC)."""
    lines = []
    for message in sorted(messages, key=lambda m: m.get("createdDateTime") or ""):
        if message.get("messageType") != "message" or message.get("deletedDateTime"):
            continue
        body = message.get("body") or {}
        html = body.get("content") if isinstance(body, dict) and body.get("content") else message.get("bodyPreview")
        text = " ".join(html_to_text(html).split())
        attachments = [a for a in (message.get("attachments") or []) if a.get("name")]
        extra = " ".join(f"[allegato: {a['name']}]" + (f" {a['contentUrl']}" if a.get("contentUrl") else "")
                         for a in attachments)
        text = " ".join(part for part in (text, extra) if part) or "[allegato]"
        stamp = (message.get("createdDateTime") or "")[11:16]
        lines.append(f"{stamp} {_sender(message)}: {text}")
    return lines


def format_duration(iso):
    """'PT1H26M21S' → '1h26'; sotto l'ora → '45 min'. None se il formato non è riconosciuto."""
    match = _DURATION.match(iso or "")
    if not match or not any(match.groups()):
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    if hours:
        return f"{hours}h{minutes:02d}"
    return f"{max(1, minutes)} min"


def attendance(messages):
    """Presenti effettivi, durata reale e registrazione, dagli eventi di sistema della chat."""
    result = {}
    for message in messages:
        detail = message.get("eventDetail") or {}
        kind = detail.get("@odata.type", "")
        if kind.endswith("callEndedEventMessageDetail"):
            names = []
            for item in detail.get("callParticipants") or []:
                person = (item.get("participant") or {}).get("user") or {}
                name = person.get("displayName")
                if name and name not in names:
                    names.append(name)
            if names:
                result["present"] = names
            duration = format_duration(detail.get("callDuration"))
            if duration:
                result["duration"] = duration
        elif kind.endswith("callRecordingEventMessageDetail"):
            if detail.get("callRecordingStatus") == "success" and detail.get("callRecordingUrl"):
                result["recording"] = detail["callRecordingUrl"]
    return result


def transcript_text(payload):
    """Il WEBVTT della riunione. Accetta la risposta MCP (dict o stringa JSON) o un VTT già estratto."""
    if payload is None:
        return None
    if isinstance(payload, str):
        if not payload.strip():
            return None
        if not payload.lstrip().startswith("{"):
            return payload
        payload = json.loads(payload)
    items = [t for t in payload.get("transcripts") or [] if t.get("content")]
    if not items:
        return None
    items.sort(key=lambda t: t.get("createdDateTime") or "")
    return "\n\n".join(t["content"] for t in items)
```

Nota: `html_to_text` scarta le righe vuote (i blocchi diventano righe singole); `format_duration("PT30S")` → `1 min` perché sotto l'ora il minimo è 1.

- [ ] **Step 4: Verifica che passino**

Run: `cd tests && python3 -m unittest test_meeting -v`
Expected: tutti PASS. Poi `python3 -m unittest discover -s tests` dalla radice: tutto OK.

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core/meeting.py tests/test_meeting.py
git commit -m "feat(toolkit): extract agenda, chat, attendance and transcript from Teams data"
```

---

### Task 2: Raw della riunione e idempotenza (`meeting.py`, parte file)

**Files:**
- Modify: `toolkit/sb_core/meeting.py` (aggiunte in coda)
- Modify: `tests/test_meeting.py` (nuove classi prima di `if __name__`)

**Interfaces:**
- Consumes: `agenda_text`, `attendance`, `chat_lines` (Task 1); `sb_core.frontmatter.render`, `sb_core.frontmatter.parse`, `sb_core.errors.FrontmatterError`.
- Produces:
  - `slug_for(subject: str | None) -> str`
  - `event_date(event: dict) -> str` — `AAAA-MM-GG`
  - `raw_path_for(root: Path, event: dict) -> Path` — percorso assoluto libero
  - `render_raw(event: dict, transcript: str | None, chat: list | None, dictation: str | None, today: date) -> str`
  - `origin_for(event: dict) -> str` — `teams:event/<id>`
  - `seen(root: Path, ids: list[str]) -> dict[str, str]` — id → percorso relativo

- [ ] **Step 1: Scrivi i test che falliscono**

Aggiungi in `tests/test_meeting.py`, in testa agli import:

```python
import datetime
from pathlib import Path

from helpers import WikiCase
from sb_core.frontmatter import parse
from sb_core.meeting import event_date, origin_for, raw_path_for, render_raw, seen, slug_for
```

e le classi:

```python
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
        root = self.make_wiki({
            "raw/2026/09/rotto.md": "---\norigin: teams:event/ID1\n",
            "raw/2026/09/bin.md": b"\xff\xfe".decode("latin-1"),
        })
        self.assertEqual(seen(root, ["ID1"]), {})

    def test_seen_without_raw_folder(self):
        self.assertEqual(seen(self.make_wiki(), ["ID1"]), {})
```

- [ ] **Step 2: Verifica che falliscano**

Run: `cd tests && python3 -m unittest test_meeting -v`
Expected: ImportError su `event_date` (e gli altri nomi nuovi).

- [ ] **Step 3: Implementa**

In `toolkit/sb_core/meeting.py` aggiorna gli import in testa:

```python
import json
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

from .errors import FrontmatterError
from .frontmatter import parse, render
```

e aggiungi in coda:

```python
_CANCELLED = re.compile(r"^\s*(annullat[ao]|cancell?ed)\s*:\s*", re.IGNORECASE)


def slug_for(subject):
    """Slug ASCII, minuscolo, a trattini, senza prefissi di annullamento; al massimo 60 caratteri."""
    text = _CANCELLED.sub("", subject or "")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    slug = slug[:60].rstrip("-")
    return slug or "riunione"


def event_date(event):
    return event["start"]["dateTime"][:10]


def origin_for(event):
    return f"teams:event/{event['id']}"


def raw_path_for(root, event):
    """raw/AAAA/MM/AAAA-MM-GG-<slug>.md; se esiste già, suffisso -2, -3…"""
    date = event_date(event)
    folder = Path(root) / "raw" / date[:4] / date[5:7]
    stem = f"{date}-{slug_for(event.get('subject'))}"
    path = folder / f"{stem}.md"
    n = 2
    while path.exists():
        path = folder / f"{stem}-{n}.md"
        n += 1
    return path


def _person(value):
    if isinstance(value, dict):
        return value.get("name") or value.get("address") or ""
    return value or ""


def _clock(stamp):
    return (stamp or "")[11:16]


def render_raw(event, transcript, chat, dictation, today):
    """Markdown del grezzo: frontmatter, evento, chat, trascrizione intatta o dettato."""
    meta = {
        "kind": "transcript" if transcript else "dictation",
        "captured": today.isoformat(),
        "origin": origin_for(event),
        "meeting_date": event_date(event),
    }
    seen_chat = attendance(chat or [])
    start, end = event.get("start") or {}, event.get("end") or {}
    when = f"{event_date(event)} {_clock(start.get('dateTime'))}–{_clock(end.get('dateTime'))}"
    when += f" {start.get('timeZone') or 'UTC'}"
    if seen_chat.get("duration"):
        when += f" · durata effettiva {seen_chat['duration']}"
    lines = [f"# {event.get('subject') or 'Riunione'}", "", "## Evento", f"- Orario: {when}"]
    organizer = _person(event.get("organizer"))
    if organizer:
        lines.append(f"- Organizzatore: {organizer}")
    invited = [p for p in (_person(a) for a in event.get("attendees") or []) if p]
    if invited:
        lines.append(f"- Invitati: {', '.join(invited)}")
    if seen_chat.get("present"):
        lines.append(f"- Presenti: {', '.join(seen_chat['present'])}")
    if seen_chat.get("recording"):
        lines.append(f"- Registrazione: {seen_chat['recording']}")
    agenda = agenda_text((event.get("body") or {}).get("content") if isinstance(event.get("body"), dict) else None)
    if agenda:
        lines += ["", "Agenda:", agenda]
    if chat is None:
        lines += ["", "## Chat", "_Chat non disponibile._"]
    else:
        messages = chat_lines(chat)
        if messages:
            lines += ["", "## Chat (orari UTC)"] + [f"- {m}" for m in messages]
    if dictation and dictation.strip():
        lines += ["", "## Dettato", dictation.strip()]
    body = "\n".join(lines) + "\n"
    if transcript:
        body += "\n## Trascrizione\n" + transcript
    return render(meta, body)


def seen(root, ids):
    """Riunioni già catturate: {id: percorso relativo del raw} per gli id trovati in raw/."""
    wanted = {origin_for({"id": i}): i for i in ids}
    found = {}
    base = Path(root) / "raw"
    if not wanted or not base.is_dir():
        return found
    for path in sorted(base.rglob("*.md")):
        try:
            meta, _ = parse(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, FrontmatterError):
            continue
        origin = (meta or {}).get("origin")
        if origin in wanted:
            found.setdefault(wanted[origin], path.relative_to(root).as_posix())
    return found
```

Nota: in `test_full_render` il corpo prima della trascrizione finisce con `\n`, poi `\n## Trascrizione\n` + VTT: il file termina esattamente con il VTT ricevuto.

- [ ] **Step 4: Verifica che passino**

Run: `cd tests && python3 -m unittest test_meeting -v`
Expected: tutti PASS. Poi `python3 -m unittest discover -s tests`: tutto OK.

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core/meeting.py tests/test_meeting.py
git commit -m "feat(toolkit): render meeting raw captures and detect already captured meetings"
```

---

### Task 3: CLI `sb meeting capture` e `sb meeting seen`

**Files:**
- Modify: `toolkit/sb_core/cli.py` (import, nuovo `_add_meeting`, handler, voce in `COMMANDS`)
- Modify: `references/conventions.md` (tabella del toolkit)
- Create: `tests/test_meeting_cli.py`

**Interfaces:**
- Consumes: `render_raw`, `raw_path_for`, `seen`, `transcript_text`, `origin_for` (Task 1–2); `Wiki`, `_today`, `_wiki` di `cli.py`.
- Produces (contratto usato dalla skill):
  - `sb meeting capture --event F [--transcript F] [--chat F] [--dictation F] [--wiki W]` → exit 0 `{"ok": true, "path": "raw/…", "kind": "transcript"|"dictation"}`; exit 1 `{"ok": false, "error": "already-captured", "path": "raw/…"}`; exit 2 `{"error": "…"}`.
  - `sb meeting seen ID… [--wiki W]` → exit 0 `{"seen": {"<id>": "raw/…"}}`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_meeting_cli.py`:

```python
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
```

- [ ] **Step 2: Verifica che falliscano**

Run: `cd tests && python3 -m unittest test_meeting_cli -v`
Expected: FAIL, argparse esce con codice 2 su `meeting` sconosciuto (le asserzioni su `data` falliscono).

- [ ] **Step 3: Implementa**

In `toolkit/sb_core/cli.py`, tra gli import:

```python
from . import meeting
```

Prima di `COMMANDS`:

```python
def _add_meeting(sub, common):
    p = sub.add_parser("meeting", help="riunioni Teams: cattura in raw/")
    msub = p.add_subparsers(dest="meeting_command", metavar="<azione>")
    msub.required = True
    cp = msub.add_parser("capture", parents=[common], help="scrive il grezzo di una riunione")
    cp.add_argument("--event", required=True, help="JSON dell'evento (read_resource calendar:///events/…)")
    cp.add_argument("--transcript", help="risposta MCP della trascrizione, o un WEBVTT")
    cp.add_argument("--chat", help="JSON: lista dei messaggi della chat della riunione")
    cp.add_argument("--dictation", help="file di testo con il dettato dell'utente")
    cp.set_defaults(handler=cmd_meeting_capture)
    sp = msub.add_parser("seen", parents=[common], help="riunioni già catturate")
    sp.add_argument("ids", nargs="*", help="id degli eventi")
    sp.set_defaults(handler=cmd_meeting_seen)


def _read_exact(path):
    """Legge un file senza tradurre i newline: la trascrizione resta byte per byte."""
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read()
    except OSError as exc:
        raise UsageError(f"impossibile leggere {path}: {exc.strerror}")


def _read_json(path, what):
    try:
        return json.loads(_read_exact(path))
    except ValueError:
        raise UsageError(f"{what}: {path} non è JSON valido")


def cmd_meeting_capture(args):
    wiki = _wiki(args)
    event = _read_json(args.event, "evento")
    if not isinstance(event, dict) or not event.get("id") or not (event.get("start") or {}).get("dateTime"):
        raise UsageError("evento: servono almeno 'id' e 'start.dateTime'")
    transcript = meeting.transcript_text(_read_exact(args.transcript)) if args.transcript else None
    dictation = _read_exact(args.dictation) if args.dictation else None
    if not transcript and not (dictation and dictation.strip()):
        raise UsageError("nessun contenuto: serve una trascrizione non vuota o --dictation")
    chat = None
    if args.chat:
        chat = _read_json(args.chat, "chat")
        if not isinstance(chat, list):
            raise UsageError("chat: serve una lista di messaggi")
    already = meeting.seen(wiki.root, [event["id"]])
    if already:
        return {"ok": False, "error": "already-captured", "path": already[event["id"]]}, 1
    path = meeting.raw_path_for(wiki.root, event)
    text = meeting.render_raw(event, transcript, chat, dictation, _today(args))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    kind = "transcript" if transcript else "dictation"
    return {"ok": True, "path": path.relative_to(wiki.root).as_posix(), "kind": kind}, 0


def cmd_meeting_seen(args):
    return {"seen": meeting.seen(_wiki(args).root, args.ids)}, 0
```

Aggiorna la lista:

```python
COMMANDS = [_add_version, _add_validate, _add_index, _add_resolve, _add_tasks, _add_sources, _add_log, _add_lint, _add_status, _add_migrate, _add_scaffold, _add_board, _add_meeting]
```

`transcript_text` riceve una stringa: se inizia con `{` viene letta come JSON MCP, altrimenti come VTT già estratto.

In `references/conventions.md`, nella tabella del toolkit, dopo la riga di `SB board`:

```markdown
| `SB meeting capture --event F [--transcript F] [--chat F] [--dictation F]` | Scrive il grezzo di una riunione Teams in `raw/`, trascrizione intatta; rifiuta una riunione già catturata |
| `SB meeting seen <id>…` | Dice quali eventi del calendario sono già stati catturati |
```

- [ ] **Step 4: Verifica che passino**

Run: `cd tests && python3 -m unittest test_meeting_cli test_meeting -v`
Expected: tutti PASS. Poi `python3 -m unittest discover -s tests`: tutto OK.

- [ ] **Step 5: Commit**

```bash
git add toolkit/sb_core/cli.py references/conventions.md tests/test_meeting_cli.py
git commit -m "feat(toolkit): sb meeting capture and seen commands"
```

---

### Task 4: Skill `/sb:meeting`, README e scenari

**Files:**
- Create: `skills/meeting/SKILL.md`
- Modify: `tests/test_plugin_layout.py` (`test_all_commands_present` + nuovo test)
- Modify: `README.md` (tabella dei comandi)
- Modify: `tests/scenarios/README.md` (scenario S9 in fondo)

**Interfaces:**
- Consumes: `SB meeting capture`, `SB meeting seen` (Task 3); passi 3–7 di `skills/put/SKILL.md`; tool MCP `outlook_calendar_search`, `read_resource`.
- Produces: la skill `meeting` del plugin.

- [ ] **Step 1: Scrivi il test che fallisce**

In `tests/test_plugin_layout.py`, aggiorna l'insieme atteso:

```python
        self.assertEqual(names, {"init", "status", "put", "sync", "ask", "prep", "report", "tasks", "lint", "schema",
                                 "board", "meeting"})
```

e aggiungi dopo `test_board_skill_controls_the_server`:

```python
    def test_meeting_skill_uses_toolkit_and_put(self):
        text = (SKILLS_DIR / "meeting" / "SKILL.md").read_text(encoding="utf-8")
        for marker in ("SB meeting capture", "SB meeting seen", "afterDateTime", "meetingTranscriptUrl",
                       "skills/put/SKILL.md", ".sb/tmp/", "--op meeting"):
            self.assertIn(marker, text)
```

- [ ] **Step 2: Verifica che fallisca**

Run: `cd tests && python3 -m unittest test_plugin_layout -v`
Expected: FAIL su `test_all_commands_present` e `FileNotFoundError` su `test_meeting_skill_uses_toolkit_and_put`.

- [ ] **Step 3: Scrivi la skill**

`skills/meeting/SKILL.md` (nota: niente recinti di codice nel file, solo blocchi indentati di 4 spazi):

````markdown
---
name: meeting
description: Fa entrare nella wiki Second Brain le riunioni Teams scaricando da Microsoft 365 evento, partecipanti, trascrizione e chat. Usa quando l'utente chiede di aggiungere o ingerire una riunione ("aggiungi la riunione appena finita", "salva la review di venerdì", "ingerisci le riunioni di oggi"), incolla un link teams.microsoft.com/meet o meetup-join, o vuole scegliere quali riunioni del giorno salvare.
argument-hint: "[oggi | ieri | AAAA-MM-GG | ultima | <link Teams> | <nome della riunione>]"
---

# /sb:meeting: riunioni Teams nella wiki

Argomenti: `$ARGUMENTS`

## 0. Prima di iniziare

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill, ed esegui `SB version`. Fuori da una wiki: fermati e proponi `/sb:init`.
2. Servono i tool Microsoft 365 `outlook_calendar_search` e `read_resource`. Se mancano o rispondono con errore di autenticazione, dillo e fermati: non ricostruire riunioni a memoria.
3. Lavora nella radice della wiki. I file temporanei vanno in `.sb/tmp/` (già ignorata da git): creala con `mkdir -p .sb/tmp`.

## 1. Trova la riunione

Cerca **sempre** con `afterDateTime` e `beforeDateTime`: la ricerca solo testuale restituisce id che `read_resource` non sa leggere. Mostra gli orari nel fuso dell'utente, convertendo dal `timeZone` dell'evento.

| Argomento | Cosa fare |
|---|---|
| nessuno, `oggi` | Modalità lista su oggi (§2) |
| `ieri`, `AAAA-MM-GG` | Modalità lista su quel giorno (§2) |
| `ultima`, "appena finita" | Cerca da 12 ore fa ad adesso con `order: newest`. Prendi il primo evento non scartato (regole in §2) che finisce entro 15 minuti da adesso. Mostra una riga ("TouchX - Metering, 11:30–12:00, 5 persone: procedo?") e attendi conferma |
| link `teams.microsoft.com/meet/<numero>` | `query: "<numero>"`, finestra da 60 giorni fa a 60 giorni avanti |
| link `…/l/meetup-join/19%3ameeting_<token>%40thread.v2…` | `query: "<token>"` nella stessa finestra. Se non trovi nulla, leggi gli eventi della finestra con lo stesso oggetto o organizzatore e confronta `onlineMeeting.joinUrl` |
| testo libero | `query` con le parole significative, nella finestra del giorno citato (data convertita in ISO), altrimenti negli ultimi 14 giorni. Un risultato: procedi. Più risultati: una domanda a scelta multipla. Nessuno: dillo e chiedi un riferimento più preciso |

I risultati arrivano a pagine di 25: segui `nextOffset` finché serve.

## 2. Modalità lista

1. Recupera tutti gli eventi del giorno, dalle 00:00 alle 23:59 nel fuso dell'utente.
2. **Scarta**: `isCancelled`; `showAs` `oof` o `free`; `isAllDay`; eventi senza partecipanti oltre all'utente (blocchi orari, pause); eventi che l'utente ha rifiutato.
3. `SB meeting seen <id> <id> …` sugli eventi rimasti.
4. Una domanda a scelta multipla (più risposte ammesse), con un'opzione per riunione **finita e non ancora catturata**: `HH:MM–HH:MM · oggetto · N persone`. Nel testo della domanda elenca a parte le riunioni già catturate e quelle non ancora finite, che non si possono scegliere.
5. Nessuna riunione selezionabile: dillo e termina.

## 3. Recupera il materiale (per ogni riunione)

Numera le riunioni scelte da 1 a n e usa quel numero nei nomi dei file.

1. **Evento**: `read_resource` dell'`uri` dell'evento. Salva il JSON così com'è in `.sb/tmp/meeting-<n>-event.json`. Se la lettura fallisce, salta la riunione e annotalo per il riepilogo.
2. **Trascrizione**: `read_resource` di `meetingTranscriptUrl`, verbatim. Se l'evento ha `recurrence` diverso da null, aggiungi `?start=<inizio ISO>&end=<fine ISO>` dell'occorrenza.
   - Se il risultato è stato salvato su file perché troppo grande, usa quel percorso.
   - Se è arrivato inline con almeno una trascrizione non vuota, salvalo intatto in `.sb/tmp/meeting-<n>-transcript.json`.
   - Se `transcripts` è vuoto o manca `meetingTranscriptUrl`: non c'è trascrizione.
3. **Chat**: dal `joinUrl` ricava il thread decodificando la parte `19%3ameeting_…%40thread.v2` (diventa `19:meeting_…@thread.v2`). Leggi `teams:///chats/<thread>/messages`. Per ogni elemento con `messageType: message` leggi anche il suo `uri` per il testo completo e sostituisci l'elemento con la versione completa. Salva la lista di tutti gli elementi, eventi di sistema compresi, come array JSON in `.sb/tmp/meeting-<n>-chat.json`. Se la chat non si legge, prosegui senza.
4. **Senza trascrizione**: dillo e chiedi "Raccontami in due righe com'è andata, oppure scrivi 'salta'". Salva la risposta intatta in `.sb/tmp/meeting-<n>-dictation.txt`. Con "salta" la riunione è esclusa (annotalo per il riepilogo).

## 4. Cattura

    SB meeting capture --event .sb/tmp/meeting-<n>-event.json [--transcript <file>] [--chat .sb/tmp/meeting-<n>-chat.json] [--dictation .sb/tmp/meeting-<n>-dictation.txt]

- exit 0: `path` è il grezzo da analizzare.
- exit 1 con `already-captured`: la riunione era già nella wiki; saltala e riportalo.
- exit 2: leggi `error`, correggi i file se il problema è tuo, altrimenti salta la riunione e riportalo.

Poi cancella i file `.sb/tmp/meeting-<n>-*` di quella riunione. Non leggere né riscrivere la trascrizione a mano: ci pensa il toolkit.

## 5. Analisi e scrittura

Per ogni grezzo catturato esegui i **passi 3, 4 e 5** di `BASE/../put/SKILL.md` (cioè `skills/put/SKILL.md`), con il grezzo come fonte. In aggiunta:

- **Tipo**: `one-on-one` se i presenti (riga `Presenti` del grezzo; se manca, `Invitati`) sono esattamente l'utente più una persona; altrimenti `meeting`.
- **Titolo**: `AAAA-MM-GG <oggetto>` con la data della riunione, senza "Annullata:" e senza i caratteri vietati (`:` diventa ` -`). Per il one-on-one vale la sua prosa: `AAAA-MM-GG 1on1 <Nome Cognome>`.
- **`series`**: solo se l'evento è ricorrente; l'oggetto senza le parti che cambiano.
- **Persone**: `SB resolve "<Nome Cognome>"` per ogni partecipante, con le regole di ambiguità. In `attendees` metti solo chi ha già una pagina o chi la prosa del tipo `person` dice di creare; gli altri restano testo semplice. Non salvare indirizzi email.
- **Estrazione**: dalla trascrizione prendi decisioni, task nei due sensi, rischi e fatti stabili; conta ciò che è stato detto, non quanto se n'è parlato. Il parlante è il nome in `<v …>`.
- **Citazioni**: `^[raw/AAAA/MM/<slug>]`; quando aiuta, il timestamp della trascrizione nel testo, per esempio "(00:15:28)".
- **`## Note`**: non compilarla. È riservata alle valutazioni dell'utente.

## 6. Chiusura

Un solo flusso di chiusura delle convenzioni per tutte le riunioni, con `--op meeting` e messaggio `<n> riunioni · <d> decisioni · <t> task` (commit `sb(meeting): …`).

## 7. Riepilogo per l'utente

- Per ogni riunione ingerita, il riepilogo del passo 7 di `put` (creato, aggiornato, task, dubbi).
- **Saltate**: oggetto e motivo (non finita, già catturata, senza trascrizione né dettato, errore del connettore).
````

Nel file reale il blocco `SB meeting capture …` del §4 è indentato di 4 spazi (come sopra), non racchiuso in recinti.

- [ ] **Step 4: README e scenario**

In `README.md`, nella tabella dei comandi, dopo la riga di `/sb:put`:

```markdown
| `/sb:meeting [oggi \| ultima \| <link> \| <nome>]` | Fa entrare riunioni Teams: trascrizione, chat, partecipanti |
```

In fondo a `tests/scenarios/README.md`:

```markdown
## S9 · `/sb:meeting` (richiede il connettore Microsoft 365 e un calendario reale)

Comandi, uno per volta:
- `/sb:meeting` → la lista di oggi esclude annullate, blocchi orari e pause; le riunioni già catturate compaiono come non selezionabili.
- `/sb:meeting <link teams.microsoft.com/meet/… di una riunione trascritta>`.
- "aggiungi la riunione appena finita" → chiede conferma con oggetto e orario prima di procedere.
- `/sb:meeting <nome di una riunione senza trascrizione>` → chiede il dettato; "salta" la esclude.

Verifiche:
- `ls raw/<anno>/<mese>/` → un grezzo per riunione con `origin: teams:event/…`; la sezione `## Trascrizione` contiene il WEBVTT;
- `SB meeting seen <id>` → restituisce il percorso del grezzo; un secondo `/sb:meeting` sulla stessa riunione la segnala come già catturata;
- `SB validate` → exit 0; esiste la pagina `meeting` o `one-on-one` con `## Note` vuota;
- `ls .sb/tmp/` → nessun file `meeting-*`;
- `git log -1 --format=%s` inizia con `sb(meeting):` e `git status --porcelain` è vuoto.
```

- [ ] **Step 5: Verifica che passi tutto**

Run: `python3 -m unittest discover -s tests` dalla radice
Expected: OK (206 + i nuovi test). Poi `claude plugin validate . --strict`: nessun errore.

- [ ] **Step 6: Commit**

```bash
git add skills/meeting/SKILL.md tests/test_plugin_layout.py README.md tests/scenarios/README.md
git commit -m "feat(skills): /sb:meeting ingests Teams meetings via Microsoft 365"
```
