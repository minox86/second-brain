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
