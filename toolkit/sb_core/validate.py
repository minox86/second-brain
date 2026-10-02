"""Validazione delle pagine contro lo schema della wiki."""
import re
from pathlib import Path

from .errors import WikiError
from .links import find_links, is_attachment, strip_code
from .names import nfc, norm, title_problem
from .wiki import COMMON_FIELDS, parse_date

_LINK_VALUE = re.compile(r"^\[\[[^\[\]]+\]\]$")
ALWAYS_ALLOWED_SYSTEMS = ("url", "mail")
AUTHORITY_VALUES = ("migrated",)


class Issue(object):
    def __init__(self, path, code, message, severity="error"):
        self.path = path
        self.code = code
        self.message = message
        self.severity = severity

    def to_dict(self):
        return {"path": self.path, "severity": self.severity, "code": self.code, "message": self.message}


def validate(wiki, paths=None):
    selected = _select(wiki, paths)
    issues = _duplicate_titles(wiki, selected)
    for page in selected:
        issues.extend(validate_page(wiki, page))
    return issues


def _relative(wiki, raw):
    path = Path(raw)
    if path.is_absolute():
        try:
            return nfc(path.resolve().relative_to(wiki.root).as_posix())
        except ValueError:
            raise WikiError(f"{raw} è fuori dalla wiki")
    from_cwd = path.resolve()
    if from_cwd.is_file():
        try:
            return nfc(from_cwd.relative_to(wiki.root).as_posix())
        except ValueError:
            pass
    text = path.as_posix()
    return nfc(text[2:] if text.startswith("./") else text)


def _select(wiki, paths):
    pages = wiki.pages()
    if not paths:
        return list(pages)
    wanted = {_relative(wiki, p) for p in paths}
    unknown = wanted - {nfc(p.path) for p in pages}
    if unknown:
        raise WikiError("pagine non trovate: " + ", ".join(sorted(unknown)))
    return [p for p in pages if nfc(p.path) in wanted]


def _duplicate_titles(wiki, selected):
    groups = {}
    for page in wiki.pages():
        groups.setdefault(norm(page.stem), []).append(page)
    selected_paths = {p.path for p in selected}
    issues = []
    for group in groups.values():
        if len(group) < 2:
            continue
        for page in group:
            if page.path in selected_paths:
                others = ", ".join(p.path for p in group if p is not page)
                issues.append(Issue(page.path, "duplicate-title", f"stesso nome di {others}: i wikilink sono ambigui"))
    return issues


def validate_page(wiki, page):
    if page.error:
        return [Issue(page.path, "bad-frontmatter", page.error)]
    if page.meta is None:
        return [Issue(page.path, "no-frontmatter", "manca il frontmatter")]
    meta = page.meta
    issues = []
    type_name = meta.get("type")
    title = meta.get("title")
    if type_name is not None and not isinstance(type_name, str):
        issues.append(Issue(page.path, "bad-value", "'type' deve essere un testo"))
        type_name = None
    elif not type_name:
        issues.append(Issue(page.path, "missing-type", "manca il campo 'type'"))
    if title is None:
        issues.append(Issue(page.path, "missing-title", "manca il campo 'title'"))
    else:
        problem = title_problem(title)
        if problem:
            issues.append(Issue(page.path, "bad-title", problem))
        elif nfc(title) != page.stem:
            issues.append(Issue(page.path, "filename-mismatch", f"il nome del file deve essere '{title}.md'"))
    typedef = wiki.types.get(type_name) if type_name else None
    if type_name and typedef is None:
        issues.append(Issue(page.path, "unknown-type", f"tipo '{type_name}' non definito in schema/types"))
    if typedef is not None:
        folder = page.path.rsplit("/", 1)[0]
        if folder != typedef.folder:
            issues.append(Issue(page.path, "wrong-folder", f"le pagine di tipo '{typedef.name}' stanno in {typedef.folder}/"))
        for field in typedef.required:
            if meta.get(field) in (None, "", []):
                issues.append(Issue(page.path, "missing-required", f"campo obbligatorio mancante: {field}"))
        for field, value in meta.items():
            if field in COMMON_FIELDS or value is None:
                continue
            spec = typedef.fields.get(field)
            if spec is None:
                issues.append(Issue(page.path, "unknown-field",
                                    f"campo '{field}' non previsto dal tipo '{typedef.name}'", "warning"))
                continue
            issues.extend(_check_value(wiki, page.path, field, value, spec))
    issues.extend(_check_common(wiki, page))
    issues.extend(_check_body_links(wiki, page))
    return issues


def _check_value(wiki, path, field, value, spec):
    kind = spec.get("kind")
    if kind == "list":
        if not isinstance(value, list):
            return [Issue(path, "bad-value", f"'{field}' deve essere una lista")]
        item_kind = spec.get("of")
        if not item_kind:
            return []
        item_spec = dict(spec, kind=item_kind)
        issues = []
        for item in value:
            issues.extend(_check_value(wiki, path, field, item, item_spec))
        return issues
    problem = _kind_problem(kind, value, spec)
    if problem:
        return [Issue(path, "bad-value", f"'{field}': {problem}")]
    if kind == "link":
        return _check_link_value(wiki, path, field, value, spec.get("to"))
    return []


def _kind_problem(kind, value, spec):
    if kind in ("string", "text"):
        return None if isinstance(value, str) else "atteso un testo"
    if kind == "date":
        return None if parse_date(value) else "attesa una data AAAA-MM-GG"
    if kind == "number":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        return None if ok else "atteso un numero"
    if kind == "bool":
        return None if isinstance(value, bool) else "atteso true o false"
    if kind == "enum":
        values = spec.get("values") or []
        return None if value in values else f"valore '{value}' non ammesso ({', '.join(map(str, values))})"
    if kind == "link":
        ok = isinstance(value, str) and _LINK_VALUE.match(value.strip())
        return None if ok else 'atteso un wikilink "[[Titolo]]"'
    return None


def _alias_issue(path, link, targets):
    canonical = targets[0].stem
    return Issue(path, "alias-link", f"[[{link.target}]] è un alias: usa [[{canonical}|{link.target}]]", "warning")


def _check_link_value(wiki, path, field, value, to_type):
    link = find_links(value)[0]
    match, targets = wiki.lookup(link.target)
    if not targets:
        return [Issue(path, "broken-link", f"'{field}' punta a [[{link.target}]], che non esiste")]
    issues = []
    if match == "alias":
        issues.append(_alias_issue(path, link, targets))
    if to_type and len(targets) == 1 and targets[0].type != to_type:
        issues.append(Issue(path, "wrong-link-type",
                            f"'{field}' deve puntare a una pagina di tipo '{to_type}': "
                            f"[[{link.target}]] è di tipo '{targets[0].type}'"))
    return issues


def _check_common(wiki, page):
    meta, path = page.meta, page.path
    issues = []
    for field in ("created", "updated", "synced"):
        if meta.get(field) is not None and parse_date(meta[field]) is None:
            issues.append(Issue(path, "bad-value", f"'{field}': attesa una data AAAA-MM-GG"))
    for field in ("aliases", "sources"):
        value = meta.get(field)
        if value is not None and not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
            issues.append(Issue(path, "bad-value", f"'{field}' deve essere una lista di testi"))
    if meta.get("external") is not None:
        issues.extend(_check_external(wiki, path, meta["external"]))
    authority = meta.get("authority")
    if authority is not None and authority not in AUTHORITY_VALUES:
        issues.append(Issue(path, "bad-value", "'authority' ammette solo: " + ", ".join(AUTHORITY_VALUES)))
    return issues


def _check_external(wiki, path, external):
    if not isinstance(external, str) or ":" not in external:
        return [Issue(path, "bad-value", "'external' deve essere '<sistema>:<riferimento>'")]
    system = external.split(":", 1)[0]
    known = set(ALWAYS_ALLOWED_SYSTEMS) | {entry.get("system") for entry in wiki.sources.values()}
    if system not in known:
        return [Issue(path, "unknown-source", f"sistema '{system}' non registrato in schema/sources.md")]
    return []


def _check_body_links(wiki, page):
    issues = []
    for link in find_links(strip_code(page.body)):
        if not link.target:
            continue
        match, targets = wiki.lookup(link.target)
        if not targets and is_attachment(link.target):
            continue
        if not targets:
            issues.append(Issue(page.path, "broken-link", f"[[{link.target}]] non esiste"))
        elif match == "alias":
            issues.append(_alias_issue(page.path, link, targets))
    return issues
