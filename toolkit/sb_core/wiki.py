"""Modello della wiki: radice, schema (tipi, soglie, sorgenti) e pagine."""
import datetime
from pathlib import Path

from . import FORMAT_VERSION
from .errors import FrontmatterError, WikiError
from .frontmatter import parse
from .names import nfc, norm

PAGE_ROOTS = ("knowledge", "operations", "outputs")
LAYER_ORDER = ("knowledge", "operations", "outputs")
SYSTEM_TYPES = ("task", "source-note")
COMMON_FIELDS = (
    "type", "title", "aliases", "created", "updated", "sources",
    "external", "version", "synced", "authority",
)
KINDS = ("string", "text", "date", "number", "bool", "enum", "link", "list")
DEFAULT_THRESHOLDS = {"stale_operations_days": 30, "one_on_one_gap_days": 21, "due_soon_days": 7}
DEFAULT_CLOSED = ("done", "dropped")
DEFAULT_SOURCE_STALE_DAYS = 30


class TypeDef(object):
    def __init__(self, name, layer, folder, fields=None, required=None, builtin=False):
        self.name = name
        self.layer = layer
        self.folder = folder
        self.fields = fields or {}
        self.required = list(required or [])
        self.builtin = builtin


BUILTIN_TYPES = (
    TypeDef("briefing", "outputs", "outputs/briefings",
            {"about": {"kind": "link"}, "for": {"kind": "date"}}, builtin=True),
    TypeDef("report", "outputs", "outputs/reports",
            {"kind": {"kind": "string"}, "scope": {"kind": "string"}, "period": {"kind": "string"}}, builtin=True),
)


class Page(object):
    def __init__(self, path, meta, body, error=None):
        self.path = path      # relativo alla radice della wiki, separatore '/'
        self.meta = meta      # dict, oppure None se il frontmatter manca o è illeggibile
        self.body = body
        self.error = error    # messaggio d'errore del frontmatter, se illeggibile

    @property
    def stem(self):
        return nfc(self.path.rsplit("/", 1)[-1][:-3])

    @property
    def type(self):
        value = (self.meta or {}).get("type")
        return value if isinstance(value, str) else None

    @property
    def title(self):
        title = (self.meta or {}).get("title")
        return title if isinstance(title, str) else self.stem

    @property
    def aliases(self):
        aliases = (self.meta or {}).get("aliases")
        if not isinstance(aliases, list):
            return []
        return [a for a in aliases if isinstance(a, str)]


def parse_date(value):
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def closed_statuses(typedef):
    spec = typedef.fields.get("status") if typedef is not None else None
    closed = spec.get("closed") if isinstance(spec, dict) else None
    return tuple(closed) if isinstance(closed, list) else DEFAULT_CLOSED


def is_open(page, typedef):
    """Un item è aperto se il suo status non è tra quelli chiusi. Un task senza status è 'todo'."""
    status = (page.meta or {}).get("status")
    if status is None:
        return page.type == "task"
    return status not in closed_statuses(typedef)


def find_root(start):
    path = Path(start).resolve()
    for candidate in [path] + list(path.parents):
        if (candidate / "schema" / "VERSION").is_file():
            return candidate
    raise WikiError(f"{path} non è dentro una wiki second-brain (manca schema/VERSION)")


def _read_meta(path):
    try:
        meta, _ = parse(path.read_text(encoding="utf-8"))
    except FrontmatterError as exc:
        raise WikiError(f"{path.name}: {exc}")
    return meta or {}


def load_types(schema_dir):
    """Carica e controlla schema/types/*.md. Aggiunge i tipi predefiniti."""
    types_dir = Path(schema_dir) / "types"
    if not types_dir.is_dir():
        raise WikiError(f"manca la cartella {types_dir}")
    types = {}
    for path in sorted(types_dir.glob("*.md")):
        meta = _read_meta(path)
        name, layer, folder = meta.get("name"), meta.get("layer"), meta.get("folder")
        if not (isinstance(name, str) and name and isinstance(folder, str) and folder):
            raise WikiError(f"{path.name}: 'name' e 'folder' sono obbligatori")
        if layer not in ("knowledge", "operations"):
            raise WikiError(f"{path.name}: 'layer' deve essere knowledge o operations")
        if not folder.startswith(layer + "/"):
            raise WikiError(f"{path.name}: 'folder' deve stare sotto {layer}/")
        fields = meta.get("fields") or {}
        if not isinstance(fields, dict) or not all(isinstance(v, dict) for v in fields.values()):
            raise WikiError(f"{path.name}: 'fields' deve associare ogni campo a {{kind: ...}}")
        for field, spec in fields.items():
            kind = spec.get("kind")
            if kind not in KINDS:
                raise WikiError(f"{path.name}: campo '{field}' ha kind '{kind}' non valido ({', '.join(KINDS)})")
            if kind == "enum" and not isinstance(spec.get("values"), list):
                raise WikiError(f"{path.name}: il campo enum '{field}' richiede 'values: [...]'")
            if kind == "list" and spec.get("of") not in (None,) + KINDS[:-1]:
                raise WikiError(f"{path.name}: 'of' del campo '{field}' non valido")
        required = meta.get("required") or []
        if not isinstance(required, list):
            raise WikiError(f"{path.name}: 'required' deve essere una lista")
        if name in types:
            raise WikiError(f"tipo duplicato: {name}")
        types[name] = TypeDef(name, layer, folder, fields, required)
    missing = [t for t in SYSTEM_TYPES if t not in types]
    if missing:
        raise WikiError("mancano i tipi di sistema: " + ", ".join(missing))
    for builtin in BUILTIN_TYPES:
        types.setdefault(builtin.name, builtin)
    return types


def _load_thresholds(schema_dir):
    thresholds = dict(DEFAULT_THRESHOLDS)
    path = schema_dir / "layers.md"
    if path.is_file():
        meta = _read_meta(path)
        for key in thresholds:
            if isinstance(meta.get(key), int) and not isinstance(meta.get(key), bool):
                thresholds[key] = meta[key]
    return thresholds


def _load_sources(schema_dir):
    path = schema_dir / "sources.md"
    if not path.is_file():
        return {}
    sources = _read_meta(path).get("sources") or {}
    if not isinstance(sources, dict) or not all(
        isinstance(e, dict) and isinstance(e.get("system"), str) for e in sources.values()
    ):
        raise WikiError("schema/sources.md: 'sources' deve associare ogni id a {system: ..., ...}")
    return sources


class Wiki(object):
    def __init__(self, path):
        self.root = find_root(path)
        schema_dir = self.root / "schema"
        raw_version = (schema_dir / "VERSION").read_text(encoding="utf-8").strip()
        try:
            self.version = int(raw_version)
        except ValueError:
            raise WikiError("schema/VERSION non contiene un numero")
        if self.version > FORMAT_VERSION:
            raise WikiError(f"wiki in formato {self.version}, il toolkit supporta fino al {FORMAT_VERSION}: aggiorna il plugin")
        if self.version < FORMAT_VERSION:
            raise WikiError(f"wiki in formato {self.version}: serve una migrazione di formato al {FORMAT_VERSION}")
        self.types = load_types(schema_dir)
        self.thresholds = _load_thresholds(schema_dir)
        self.sources = _load_sources(schema_dir)
        self.invalidate()

    def invalidate(self):
        """Dimentica le pagine lette: da chiamare dopo aver scritto su disco."""
        self._pages = None
        self._by_path = None
        self._by_stem = None
        self._by_alias = None

    def pages(self):
        if self._pages is None:
            pages = []
            for root_name in PAGE_ROOTS:
                base = self.root / root_name
                if not base.is_dir():
                    continue
                for path in sorted(base.rglob("*.md")):
                    rel = path.relative_to(self.root).as_posix()
                    try:
                        text = path.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        pages.append(Page(rel, None, "", "il file non è UTF-8"))
                        continue
                    try:
                        meta, body = parse(text)
                    except FrontmatterError as exc:
                        pages.append(Page(rel, None, text, str(exc)))
                        continue
                    pages.append(Page(rel, meta, body))
            self._pages = pages
        return self._pages

    def _build_indexes(self):
        if self._by_stem is not None:
            return
        by_path, by_stem, by_alias = {}, {}, {}
        for page in self.pages():
            by_path[page.path] = page
            by_path.setdefault(nfc(page.path), page)
            by_stem.setdefault(norm(page.stem), []).append(page)
            for alias in page.aliases:
                by_alias.setdefault(norm(alias), []).append(page)
        self._by_path, self._by_stem, self._by_alias = by_path, by_stem, by_alias

    def page(self, rel):
        self._build_indexes()
        return self._by_path.get(rel) or (self._by_path.get(nfc(rel)) if isinstance(rel, str) else None)

    def identity(self, name):
        """Chiave stabile di un nome: il path della pagina se si risolve in modo univoco, altrimenti il nome normalizzato."""
        if not name:
            return None
        _, pages = self.lookup(name)
        return pages[0].path if len(pages) == 1 else norm(name)

    def lookup(self, name):
        """Risolve il target di un wikilink come Obsidian (nome file), poi per alias."""
        self._build_indexes()
        key = norm(name)
        if key in self._by_stem:
            return "stem", self._by_stem[key]
        if key in self._by_alias:
            return "alias", self._by_alias[key]
        return None, []
