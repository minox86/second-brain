"""Wikilink in stile Obsidian: [[Titolo]], [[Titolo#sezione]], [[Titolo|testo]]."""
import re
from collections import namedtuple

WIKILINK = re.compile(r"\[\[([^\[\]\n]+?)\]\]")

Link = namedtuple("Link", "target heading display")


def parse_link(inner):
    target, _, display = inner.partition("|")
    target, _, heading = target.partition("#")
    target = target.strip().rsplit("/", 1)[-1]
    if target.lower().endswith(".md"):
        target = target[:-3]
    return Link(target.strip(), heading.strip() or None, display.strip() or None)


def find_links(text):
    return [parse_link(m.group(1)) for m in WIKILINK.finditer(text or "")]


def links_in_value(value):
    """Wikilink contenuti in un valore di frontmatter (stringa, lista o mappa)."""
    if isinstance(value, str):
        return find_links(value)
    if isinstance(value, list):
        return [link for item in value for link in links_in_value(item)]
    if isinstance(value, dict):
        return [link for item in value.values() for link in links_in_value(item)]
    return []


def page_links(page):
    """Tutti i wikilink di una pagina: frontmatter + corpo."""
    return links_in_value(page.meta or {}) + find_links(page.body)


def link_target_name(value):
    """Nome del target per un valore come "[[Luca|L]]"; testo semplice ripulito; None se vuoto."""
    if not isinstance(value, str):
        return None
    links = find_links(value)
    if links:
        return links[0].target or None
    return value.strip() or None


def graph(wiki):
    """Grafo dei link risolti in modo univoco: (uscenti, entranti) per path di pagina."""
    pages = [p for p in wiki.pages() if p.meta is not None]
    outgoing = {p.path: set() for p in pages}
    incoming = {p.path: set() for p in pages}
    for page in pages:
        for link in page_links(page):
            if not link.target:
                continue
            _, targets = wiki.lookup(link.target)
            if len(targets) != 1:
                continue
            target = targets[0].path
            if target != page.path and target in incoming:
                outgoing[page.path].add(target)
                incoming[target].add(page.path)
    return outgoing, incoming
