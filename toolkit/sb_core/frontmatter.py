"""Parser e serializzatore del sottoinsieme YAML usato nel frontmatter.

Grammatica supportata:
- righe `chiave: valore` al primo livello;
- `chiave:` seguita da un blocco indentato: una lista (`- valore`) oppure
  una mappa di un solo livello (`sotto: valore`);
- valori: stringhe tra virgolette o nude, interi, decimali, true/false,
  null/~, liste `[a, b]` e mappe `{k: v}` annidabili;
- commenti `#` a inizio riga o preceduti da spazio, fuori dalle virgolette.
Un valore nudo che inizia con `[[` è una stringa (wikilink).
Le date restano stringhe.
"""
import re

from .errors import FrontmatterError

_INT = re.compile(r"-?\d+$")
_FLOAT = re.compile(r"-?\d+\.\d+$")
_RESERVED = {"", "null", "~", "true", "false"}
_QUOTE_OPENERS = " \t[{,:"


def split(text):
    """Separa frontmatter e corpo. Ritorna (testo_frontmatter | None, corpo)."""
    text = text.replace("\r\n", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]
    if not text.startswith("---\n"):
        return None, text
    lines = text.split("\n")
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    raise FrontmatterError("frontmatter non chiuso: manca la riga '---'")


def parse(text):
    """Ritorna (meta | None, corpo). meta è None se il frontmatter manca."""
    fm, body = split(text)
    if fm is None:
        return None, body
    return _parse_mapping(fm), body


def _parse_mapping(src):
    result = {}
    lines = src.split("\n")
    i = 0
    while i < len(lines):
        line = _strip_comment(lines[i])
        if not line.strip():
            i += 1
            continue
        if line[0] in " \t":
            raise FrontmatterError(f"riga {i + 1}: indentazione inattesa")
        key, rest = _split_key(line, i + 1)
        i += 1
        if rest:
            result[key] = parse_value(rest)
            continue
        block = []
        while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t" or _is_item(lines[i])):
            stripped = _strip_comment(lines[i]).strip()
            if stripped:
                block.append((i + 1, stripped))
            i += 1
        result[key] = _parse_block(block)
    return result


def _is_item(line):
    return line.rstrip() == "-" or line.startswith("- ")


def _split_key(line, lineno):
    key, sep, rest = line.partition(":")
    key = key.strip()
    if not sep or not key:
        raise FrontmatterError(f"riga {lineno}: attesa 'chiave: valore'")
    return key, rest.strip()


def _parse_block(block):
    if not block:
        return None
    if all(text == "-" or text.startswith("- ") for _, text in block):
        items = []
        for lineno, text in block:
            if text == "-":
                raise FrontmatterError(f"riga {lineno}: elemento di lista vuoto")
            items.append(parse_value(text[2:]))
        return items
    if any(text == "-" or text.startswith("- ") for _, text in block):
        raise FrontmatterError(f"riga {block[0][0]}: lista e mappa mescolate nello stesso blocco")
    mapping = {}
    for lineno, text in block:
        key, rest = _split_key(text, lineno)
        if not rest:
            raise FrontmatterError(f"riga {lineno}: annidamento oltre un livello non supportato")
        mapping[key] = parse_value(rest)
    return mapping


def _strip_comment(line):
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if quote == '"' and ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'" and (i == 0 or line[i - 1] in _QUOTE_OPENERS):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
        i += 1
    return line


def parse_value(text):
    """Interpreta un valore (scalare, lista o mappa) scritto su una riga."""
    text = text.strip()
    value, pos = _parse(text, 0, "")
    if text[pos:].strip():
        raise FrontmatterError(f"contenuto inatteso dopo il valore: {text[pos:]!r}")
    return value


def _skip_ws(s, pos):
    while pos < len(s) and s[pos] in " \t":
        pos += 1
    return pos


def _parse(s, pos, stops):
    pos = _skip_ws(s, pos)
    if pos >= len(s):
        if stops:
            raise FrontmatterError("valore mancante")
        return None, pos
    ch = s[pos]
    if ch == "[" and not s.startswith("[[", pos):
        return _parse_list(s, pos + 1)
    if ch == "{":
        return _parse_map(s, pos + 1)
    if ch in "\"'":
        return _parse_quoted(s, pos)
    end = _scalar_end(s, pos, stops)
    return _scalar(s[pos:end].strip()), end


def _parse_list(s, pos):
    items = []
    pos = _skip_ws(s, pos)
    if pos < len(s) and s[pos] == "]":
        return items, pos + 1
    while True:
        value, pos = _parse(s, pos, ",]")
        items.append(value)
        pos = _skip_ws(s, pos)
        if pos >= len(s):
            raise FrontmatterError("lista non chiusa: manca ']'")
        if s[pos] == ",":
            pos += 1
            continue
        if s[pos] == "]":
            return items, pos + 1
        raise FrontmatterError(f"carattere inatteso nella lista: {s[pos]!r}")


def _parse_map(s, pos):
    mapping = {}
    pos = _skip_ws(s, pos)
    if pos < len(s) and s[pos] == "}":
        return mapping, pos + 1
    while True:
        colon = s.find(":", pos)
        if colon == -1:
            raise FrontmatterError("mappa non valida: manca ':'")
        key = s[pos:colon].strip()
        if not key:
            raise FrontmatterError("mappa non valida: chiave vuota")
        value, pos = _parse(s, colon + 1, ",}")
        mapping[key] = value
        pos = _skip_ws(s, pos)
        if pos >= len(s):
            raise FrontmatterError("mappa non chiusa: manca '}'")
        if s[pos] == ",":
            pos = _skip_ws(s, pos + 1)
            continue
        if s[pos] == "}":
            return mapping, pos + 1
        raise FrontmatterError(f"carattere inatteso nella mappa: {s[pos]!r}")


def _parse_quoted(s, pos):
    quote = s[pos]
    out = []
    i = pos + 1
    while i < len(s):
        ch = s[i]
        if quote == '"' and ch == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            out.append({"n": "\n", "t": "\t"}.get(nxt, nxt))
            i += 2
            continue
        if ch == quote:
            if quote == "'" and s.startswith("''", i):
                out.append("'")
                i += 2
                continue
            return "".join(out), i + 1
        out.append(ch)
        i += 1
    raise FrontmatterError("stringa tra virgolette non chiusa")


def _scalar_end(s, pos, stops):
    i = pos
    while i < len(s):
        if s.startswith("[[", i):
            close = s.find("]]", i)
            if close == -1:
                raise FrontmatterError("wikilink non chiuso: manca ']]'")
            i = close + 2
            continue
        if s[i] in stops:
            break
        i += 1
    return i


def _scalar(token):
    if token in ("", "null", "~"):
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    if _INT.match(token):
        return int(token)
    if _FLOAT.match(token):
        return float(token)
    return token


def dump(meta):
    """Serializza una mappa nel sottoinsieme YAML. Le mappe di primo livello diventano blocchi."""
    lines = []
    for key, value in meta.items():
        if isinstance(value, dict) and value:
            lines.append(f"{key}:")
            for sub, subvalue in value.items():
                lines.append(f"  {sub}: {_flow(subvalue)}")
        else:
            lines.append(f"{key}: {_flow(value)}")
    return "".join(line + "\n" for line in lines)


def render(meta, body):
    """Ricompone una pagina: frontmatter + corpo."""
    return "---\n" + dump(meta) + "---\n" + body


def _flow(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_flow(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {_flow(v)}" for k, v in value.items()) + "}"
    return _string(str(value))


def _string(text):
    if not _needs_quotes(text):
        return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
    return f'"{escaped}"'


def _needs_quotes(text):
    if text in _RESERVED or text != text.strip():
        return True
    if _INT.match(text) or _FLOAT.match(text):
        return True
    if text[0] in "[]{}\"'#&*!|>%@`,?:-":
        return True
    return any(c in text for c in ",[]{}\n\t") or ": " in text or " #" in text


_KEY_LINE = re.compile(r"^([^\s#:-][^:]*):")


def update_text(text, changes):
    """Modifica solo i campi indicati del frontmatter (None li rimuove); il resto resta identico."""
    fm, body = split(text)
    if fm is None:
        fresh = {k: v for k, v in changes.items() if v is not None}
        return render(fresh, body) if fresh else body
    lines = fm.split("\n") if fm else []
    for key, value in changes.items():
        new_lines = [] if value is None else dump({key: value}).rstrip("\n").split("\n")
        spans = _key_spans(lines)
        if key in spans:
            start, end = spans[key]
            lines[start:end] = new_lines
        elif value is not None:
            insert_at = len(lines)
            while insert_at > 0 and not lines[insert_at - 1].strip():
                insert_at -= 1
            lines[insert_at:insert_at] = new_lines
    inner = "\n".join(lines) + "\n" if lines else ""
    return "---\n" + inner + "---\n" + body


def _key_spans(lines):
    """Per ogni chiave di primo livello: (prima riga, riga dopo l'ultima) del suo valore."""
    spans = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        match = None
        if line and line[0] not in " \t#" and not _is_item(line):
            match = _KEY_LINE.match(line)
        if not match:
            i += 1
            continue
        start = i
        i += 1
        while i < len(lines) and lines[i].strip() and (lines[i][0] in " \t" or _is_item(lines[i])):
            i += 1
        spans[match.group(1).strip()] = (start, i)
    return spans
