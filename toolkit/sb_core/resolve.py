"""Risoluzione di un nome libero verso le pagine della wiki, con punteggio."""
from difflib import SequenceMatcher

from .names import fold, norm

FUZZY_THRESHOLD = 0.5


def resolve(wiki, name, type_name=None, limit=5):
    query = norm(name)
    folded = fold(name)
    tokens = set(folded.split())
    candidates = []
    for page in wiki.pages():
        if page.meta is None or (type_name and page.type != type_name):
            continue
        score, match = _score(page, query, folded, tokens)
        if score >= FUZZY_THRESHOLD:
            candidates.append({
                "path": page.path, "title": page.title, "type": page.type,
                "score": score, "match": match,
            })
    candidates.sort(key=lambda c: (-c["score"], norm(c["title"])))
    return {"query": name, "candidates": candidates[:limit]}


def _score(page, query, folded, tokens):
    if norm(page.title) == query or norm(page.stem) == query:
        return 1.0, "title"
    if query in [norm(a) for a in page.aliases]:
        return 0.9, "alias"
    names = [page.title] + page.aliases
    if tokens and any(tokens <= set(fold(n).split()) for n in names):
        return 0.75, "partial"
    best = max(SequenceMatcher(None, folded, fold(n)).ratio() for n in names)
    return round(best * 0.7, 3), "fuzzy"
