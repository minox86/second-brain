"""Lint strutturale: validazione + orfani, sorgenti stantie, task scaduti, item fermi."""
from .links import graph
from .sources import stale_sources
from .tasks import list_tasks
from .validate import Issue, validate
from .wiki import is_open, parse_date


def lint(wiki, today):
    issues = list(validate(wiki))
    issues.extend(_orphans(wiki))
    for item in stale_sources(wiki, today):
        detail = "mai sincronizzata" if item["age_days"] is None else f"sincronizzata {item['age_days']} giorni fa"
        issues.append(Issue(item["path"], "stale-source", f"sorgente da riallineare ({detail})", "warning"))
    for task in list_tasks(wiki, view="overdue", today=today):
        issues.append(Issue(task["path"], "overdue-task", f"task scaduto il {task['due']}", "warning"))
    issues.extend(_stale_items(wiki, today))
    return issues


def _orphans(wiki):
    outgoing, incoming = graph(wiki)
    return [
        Issue(path, "orphan", "nessun link in entrata né in uscita", "warning")
        for path in sorted(outgoing)
        if not outgoing[path] and not incoming[path] and not path.startswith("outputs/")
    ]


def _stale_items(wiki, today):
    limit = wiki.thresholds["stale_operations_days"]
    issues = []
    for page in wiki.pages():
        if page.meta is None:
            continue
        typedef = wiki.types.get(page.type)
        if typedef is None or typedef.layer != "operations" or "status" not in typedef.fields:
            continue
        if not is_open(page, typedef):
            continue
        last = parse_date(page.meta.get("updated")) or parse_date(page.meta.get("created"))
        if last is None:
            continue
        age = (today - last).days
        if age > limit:
            issues.append(Issue(page.path, "stale-item", f"aperto e senza aggiornamenti da {age} giorni", "warning"))
    return issues
