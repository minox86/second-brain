"""Dati del cruscotto /sb:status."""
import re

from .lint import lint
from .links import link_target_name
from .names import norm
from .sources import stale_sources
from .tasks import list_tasks
from .wiki import closed_statuses, parse_date

_OPEN_PROPOSAL = re.compile(r"^\s*- \[ \] ", re.MULTILINE)


def status(wiki, today):
    overdue = list_tasks(wiki, view="overdue", today=today)
    week = list_tasks(wiki, view="week", today=today)
    issues = lint(wiki, today)
    return {
        "today": today.isoformat(),
        "tasks": {
            "overdue": [t for t in overdue if not t["delegated"]],
            "due_soon": [t for t in week if not t["overdue"]],
            "delegated_overdue": [t for t in overdue if t["delegated"]],
        },
        "one_on_one_gaps": one_on_one_gaps(wiki, today),
        "stale_sources": stale_sources(wiki, today),
        "open_proposals": count_open_proposals(wiki),
        "lint": {
            "errors": sum(1 for i in issues if i.severity == "error"),
            "warnings": sum(1 for i in issues if i.severity == "warning"),
        },
    }


def one_on_one_gaps(wiki, today):
    if "one-on-one" not in wiki.types:
        return []
    gap = wiki.thresholds["one_on_one_gap_days"]
    last = {}
    for page in wiki.pages():
        if page.meta is None or page.type != "one-on-one":
            continue
        person = link_target_name(page.meta.get("with"))
        when = parse_date(page.meta.get("date")) or parse_date(page.meta.get("created"))
        if not person or when is None:
            continue
        _, targets = wiki.lookup(person)
        if len(targets) == 1:
            target = targets[0]
            if _has_left(wiki, target):
                continue
            key, person = target.path, target.title
        else:
            key = norm(person)
        if key not in last or when > last[key][1]:
            last[key] = (person, when)
    gaps = [
        {"person": person, "last": when.isoformat(), "days": (today - when).days}
        for person, when in last.values()
        if (today - when).days > gap
    ]
    gaps.sort(key=lambda g: (-g["days"], norm(g["person"])))
    return gaps


def _has_left(wiki, page):
    status = (page.meta or {}).get("status")
    return status is not None and status in closed_statuses(wiki.types.get(page.type))


def count_open_proposals(wiki):
    path = wiki.root / "schema" / "proposals.md"
    if not path.is_file():
        return 0
    return len(_OPEN_PROPOSAL.findall(path.read_text(encoding="utf-8")))
