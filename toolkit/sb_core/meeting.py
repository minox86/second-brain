"""Riunioni Teams: dal materiale scaricato via Microsoft 365 al grezzo in raw/."""
import json
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

from .errors import FrontmatterError
from .frontmatter import parse, render

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


def _is_webvtt(text):
    return text.lstrip("﻿ \t\r\n").startswith("WEBVTT")


def transcript_text(payload):
    """Il WEBVTT della riunione. Accetta la risposta MCP (dict o stringa JSON) o un VTT già estratto.

    Solleva ValueError se il contenuto non è riconoscibile come trascrizione: un grezzo sbagliato
    resterebbe per sempre in raw/ e bloccherebbe una nuova cattura."""
    if payload is None:
        return None
    if isinstance(payload, str):
        if not payload.strip():
            return None
        if not payload.lstrip().startswith("{"):
            if not _is_webvtt(payload):
                raise ValueError("non è un WEBVTT")
            return payload
        payload = json.loads(payload)
    transcripts = payload.get("transcripts") if isinstance(payload, dict) else None
    if transcripts is not None and not isinstance(transcripts, list):
        raise ValueError("'transcripts' non è una lista")
    items = [t for t in transcripts or [] if isinstance(t, dict) and t.get("content")]
    if not items:
        return None
    if not all(isinstance(t["content"], str) and _is_webvtt(t["content"]) for t in items):
        raise ValueError("il contenuto non è un WEBVTT")
    items.sort(key=lambda t: t.get("createdDateTime") or "")
    return "\n\n".join(t["content"] for t in items)


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
    body_html = event["body"].get("content") if isinstance(event.get("body"), dict) else None
    agenda = agenda_text(body_html)
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
        if isinstance(origin, str) and origin in wanted:
            found.setdefault(wanted[origin], path.relative_to(root).as_posix())
    return found
