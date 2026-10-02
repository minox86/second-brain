"""Registro cronologico delle operazioni (log.md, solo in aggiunta)."""
import datetime
from pathlib import Path

from .errors import UsageError

LOG_HEADER = "# Log\n\nRegistro cronologico delle operazioni sulla wiki (solo in aggiunta).\n\n"


def append_log(root, message, op="note", now=None):
    message = " ".join(str(message).split())
    op = " ".join(str(op).split()) or "note"
    if not message:
        raise UsageError("il messaggio di log è vuoto")
    now = now or datetime.datetime.now()
    line = f"- {now:%Y-%m-%d %H:%M} · {op} · {message}"
    path = Path(root) / "log.md"
    if not path.exists():
        path.write_text(LOG_HEADER, encoding="utf-8")
    existing = path.read_text(encoding="utf-8")
    prefix = "" if existing.endswith("\n") or not existing else "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(prefix + line + "\n")
    return {"logged": line}
