"""Normalizzazione dei nomi e regole sui titoli (titolo = nome del file)."""
import unicodedata

FORBIDDEN_TITLE_CHARS = '\\/:*?"<>|#^[]'


def nfc(text):
    """Forma Unicode composta: macOS può restituire nomi file decomposti (NFD)."""
    return unicodedata.normalize("NFC", text)


def norm(name):
    """Confronto case-insensitive con spazi compressi, come fa Obsidian sui nomi file."""
    return " ".join(nfc(str(name)).split()).casefold()


def fold(name):
    """norm + rimozione degli accenti, per i confronti approssimati."""
    decomposed = unicodedata.normalize("NFKD", norm(name))
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def title_problem(title):
    """Motivo per cui il titolo non può essere un nome file, oppure None se va bene."""
    if not isinstance(title, str) or not title.strip():
        return "titolo vuoto o non testuale"
    if title != title.strip():
        return "il titolo ha spazi iniziali o finali"
    if title.startswith("."):
        return "il titolo non può iniziare con '.'"
    bad = sorted({c for c in title if c in FORBIDDEN_TITLE_CHARS})
    if bad:
        return "caratteri non ammessi nel titolo: " + " ".join(bad)
    return None
