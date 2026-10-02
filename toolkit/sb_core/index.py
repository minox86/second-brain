"""Indice generato (index.md) e mappa dei backlink (.sb/backlinks.json)."""
import json

from .links import graph
from .names import norm
from .wiki import LAYER_ORDER

INDEX_HEADER = "# Indice\n\n> Generato da `sb index`: non modificare a mano."


def _indexed_pages(wiki):
    return [p for p in wiki.pages() if p.meta is not None and p.type in wiki.types]


def build_index(wiki):
    pages = _indexed_pages(wiki)
    sections = [INDEX_HEADER]
    for layer in LAYER_ORDER:
        blocks = []
        layer_types = sorted((t for t in wiki.types.values() if t.layer == layer), key=lambda t: t.name)
        for typedef in layer_types:
            members = sorted((p for p in pages if p.type == typedef.name), key=lambda p: norm(p.stem))
            if not members:
                continue
            lines = [f"### {typedef.name} ({len(members)})"]
            for page in members:
                date = page.meta.get("updated") or page.meta.get("created")
                suffix = f" · {date}" if date else ""
                lines.append(f"- [[{page.stem}]]{suffix}")
            blocks.append("\n".join(lines))
        if blocks:
            sections.append(f"## {layer}\n\n" + "\n\n".join(blocks))
    return "\n\n".join(sections) + "\n"


def build_backlinks(wiki):
    _, incoming = graph(wiki)
    return {target: sorted(sources) for target, sources in sorted(incoming.items()) if sources}


def write_index(wiki):
    (wiki.root / "index.md").write_text(build_index(wiki), encoding="utf-8")
    sb_dir = wiki.root / ".sb"
    sb_dir.mkdir(exist_ok=True)
    backlinks = build_backlinks(wiki)
    (sb_dir / "backlinks.json").write_text(
        json.dumps(backlinks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"pages": len(_indexed_pages(wiki)), "index": "index.md", "backlinks": ".sb/backlinks.json"}
