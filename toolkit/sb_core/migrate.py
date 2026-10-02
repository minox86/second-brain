"""Migrazioni della wiki: spostamenti, cambi di titolo, rinomina e modifica di campi.

Il piano viene applicato prima in memoria; i file vengono toccati solo se tutte
le operazioni sono valide.
"""
import json
import os
from pathlib import Path

from .errors import PlanError
from .frontmatter import render
from .links import WIKILINK, parse_link
from .names import nfc, norm, title_problem
from .wiki import PAGE_ROOTS


def load_plan(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PlanError(f"piano illeggibile: {exc}")
    ops = data.get("ops") if isinstance(data, dict) else None
    if not isinstance(ops, list) or not ops:
        raise PlanError("il piano deve contenere una lista 'ops' non vuota")
    return ops


class _Context(object):
    def __init__(self, wiki):
        self.wiki = wiki
        self.state = {p.path: [dict(p.meta), p.body] for p in wiki.pages() if p.meta is not None}
        # pagine senza frontmatter leggibile: non si spostano, ma i loro link si riscrivono
        self.raw = {p.path: p.body for p in wiki.pages() if p.meta is None}
        self.raw_touched = set()
        self.touched = set()
        self.moves = []
        self.moved_from = set()

    def require(self, path, index):
        if not isinstance(path, str) or path not in self.state:
            raise PlanError(f"operazione {index}: pagina '{path}' non trovata o con frontmatter illeggibile")

    def check_destination(self, src, dst, index):
        if not isinstance(dst, str) or not dst.endswith(".md") or dst.startswith("/") or ".." in dst.split("/"):
            raise PlanError(f"operazione {index}: la destinazione deve essere un percorso .md relativo alla wiki")
        if dst.split("/", 1)[0] not in PAGE_ROOTS:
            raise PlanError(f"operazione {index}: la destinazione deve stare sotto {', '.join(PAGE_ROOTS)}/")
        if dst == src:
            return
        if dst in self.state:
            raise PlanError(f"operazione {index}: '{dst}' esiste già")
        # macOS è case-insensitive: due percorsi che differiscono solo per maiuscole sono lo stesso file
        folded = norm(dst)
        if any(norm(p) == folded for p in list(self.state) + list(self.raw) if p != src):
            raise PlanError(f"operazione {index}: '{dst}' coincide con una pagina esistente (maiuscole/minuscole)")
        dst_abs, src_abs = self.wiki.root / dst, self.wiki.root / src
        if dst_abs.exists() and dst not in self.moved_from:
            same_file = src_abs.exists() and os.path.samefile(str(src_abs), str(dst_abs))
            if not same_file:
                raise PlanError(f"operazione {index}: '{dst}' esiste già")

    def move(self, src, dst):
        if dst == src:
            return
        self.state[dst] = self.state.pop(src)
        self.moves.append((src, dst))
        self.moved_from.add(src)
        if src in self.touched:
            self.touched.discard(src)
            self.touched.add(dst)


def _apply_fields(meta, fields, index):
    if not isinstance(fields, dict):
        raise PlanError(f"operazione {index}: i campi devono essere una mappa")
    for key, value in fields.items():
        if value is None:
            meta.pop(key, None)
        else:
            meta[key] = value


def _op_move(ctx, op, index):
    src, dst = op.get("path"), op.get("to")
    ctx.require(src, index)
    ctx.check_destination(src, dst, index)
    ctx.move(src, dst)
    fields = op.get("set")
    if fields:
        _apply_fields(ctx.state[dst][0], fields, index)
        ctx.touched.add(dst)
    change = {"op": "move", "path": src, "to": dst}
    old_stem, new_stem = _stem(src), _stem(dst)
    if old_stem != new_stem:
        change["links_rewritten"] = _rewrite_links(ctx, old_stem, new_stem)
    return [change]


def _stem(path):
    return nfc(path.rsplit("/", 1)[-1][:-3])


def _op_relink(ctx, op, index):
    old, new = op.get("from"), op.get("to")
    if not (isinstance(old, str) and old.strip() and isinstance(new, str) and new.strip()):
        raise PlanError(f"operazione {index}: 'from' e 'to' devono essere titoli")
    problem = title_problem(new)
    if problem:
        raise PlanError(f"operazione {index}: 'to' non valido: {problem}")
    return [{"op": "relink", "from": old, "to": new, "links_rewritten": _rewrite_links(ctx, old, new)}]


def _op_retitle(ctx, op, index):
    path, new_title = op.get("path"), op.get("title")
    ctx.require(path, index)
    problem = title_problem(new_title)
    if problem:
        raise PlanError(f"operazione {index}: titolo non valido: {problem}")
    folder, filename = path.rsplit("/", 1)
    old_title = nfc(filename[:-3])
    new_path = f"{folder}/{new_title}.md"
    ctx.check_destination(path, new_path, index)
    ctx.move(path, new_path)
    meta = ctx.state[new_path][0]
    meta["title"] = new_title
    if norm(old_title) != norm(new_title):
        aliases = [a for a in (meta.get("aliases") or []) if isinstance(a, str)]
        if old_title not in aliases:
            aliases.append(old_title)
        meta["aliases"] = aliases
    ctx.touched.add(new_path)
    count = _rewrite_links(ctx, old_title, new_title)
    return [{"op": "retitle", "path": path, "to": new_path, "links_rewritten": count}]


def _rewrite_links(ctx, old, new):
    key = norm(old)
    counter = [0]

    def replace(match):
        link = parse_link(match.group(1))
        if norm(link.target) != key:
            return match.group(0)
        counter[0] += 1
        text = new
        if link.heading:
            text += "#" + link.heading
        if link.display:
            text += "|" + link.display
        return "[[" + text + "]]"

    def rewrite(value):
        if isinstance(value, str):
            return WIKILINK.sub(replace, value)
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        if isinstance(value, dict):
            return {k: rewrite(v) for k, v in value.items()}
        return value

    for path, entry in ctx.state.items():
        new_meta, new_body = rewrite(entry[0]), rewrite(entry[1])
        if new_meta != entry[0] or new_body != entry[1]:
            entry[0], entry[1] = new_meta, new_body
            ctx.touched.add(path)
    for path, text in list(ctx.raw.items()):
        new_text = rewrite(text)
        if new_text != text:
            ctx.raw[path] = new_text
            ctx.raw_touched.add(path)
    return counter[0]


def _op_rename_field(ctx, op, index):
    type_name, old, new = op.get("type"), op.get("from"), op.get("to")
    if not all(isinstance(x, str) and x for x in (type_name, old, new)):
        raise PlanError(f"operazione {index}: 'type', 'from' e 'to' sono obbligatori")
    changes = []
    for path in sorted(ctx.state):
        meta = ctx.state[path][0]
        if meta.get("type") != type_name or old not in meta:
            continue
        if new in meta:
            raise PlanError(f"operazione {index}: {path} ha già il campo '{new}'")
        ctx.state[path][0] = {(new if k == old else k): v for k, v in meta.items()}
        ctx.touched.add(path)
        changes.append({"op": "rename_field", "path": path, "from": old, "to": new})
    return changes


def _op_set(ctx, op, index):
    path, fields = op.get("path"), op.get("fields")
    ctx.require(path, index)
    if not fields:
        raise PlanError(f"operazione {index}: 'fields' è obbligatorio")
    _apply_fields(ctx.state[path][0], fields, index)
    ctx.touched.add(path)
    return [{"op": "set", "path": path, "fields": sorted(fields)}]


OPS = {"move": _op_move, "retitle": _op_retitle, "rename_field": _op_rename_field, "set": _op_set, "relink": _op_relink}


def migrate(wiki, ops, dry_run=False):
    if not isinstance(ops, list) or not ops:
        raise PlanError("il piano deve contenere almeno un'operazione")
    ctx = _Context(wiki)
    changes = []
    for index, op in enumerate(ops, 1):
        kind = op.get("op") if isinstance(op, dict) else None
        if kind not in OPS:
            raise PlanError(f"operazione {index}: 'op' sconosciuta ({kind}); ammesse: {', '.join(OPS)}")
        changes.extend(OPS[kind](ctx, op, index))
    if not dry_run:
        _apply(ctx)
    written = sorted(ctx.touched | ctx.raw_touched)
    return {"dry_run": dry_run, "changes": changes, "written": [] if dry_run else written}


def _apply(ctx):
    root = ctx.wiki.root
    for src, dst in ctx.moves:
        target = root / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        os.rename(str(root / src), str(target))
    for path in sorted(ctx.touched):
        meta, body = ctx.state[path]
        (root / path).write_text(render(meta, body), encoding="utf-8")
    for path in sorted(ctx.raw_touched):
        (root / path).write_text(ctx.raw[path], encoding="utf-8")
    ctx.wiki.invalidate()
