"""Query sui task: viste, filtri e record JSON (contratto per gli artefatti)."""
import datetime

from .errors import UsageError
from .links import link_target_name
from .names import norm
from .wiki import closed_statuses, parse_date

VIEWS = ("mine", "delegated", "overdue", "today", "week", "blocked", "all")
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _iso(value):
    date = parse_date(value)
    return date.isoformat() if date else None


def task_record(page, today, closed):
    meta = page.meta
    status = meta.get("status") if isinstance(meta.get("status"), str) else "todo"
    owner = link_target_name(meta.get("owner"))
    due = parse_date(meta.get("due"))
    related = meta.get("related") if isinstance(meta.get("related"), list) else []
    priority = meta.get("priority")
    return {
        "path": page.path,
        "title": page.title,
        "status": status,
        "owner": owner,
        "delegated": owner is not None,
        "due": due.isoformat() if due else None,
        "overdue": bool(due and status not in closed and due < today),
        "priority": priority if isinstance(priority, str) else None,
        "related": [name for name in (link_target_name(r) for r in related) if name],
        "created": _iso(meta.get("created")),
    }


def list_tasks(wiki, view="mine", project=None, person=None, priority=None, today=None):
    if view not in VIEWS:
        raise UsageError(f"vista sconosciuta: {view} ({', '.join(VIEWS)})")
    today = today or datetime.date.today()
    closed = closed_statuses(wiki.types["task"])
    horizon = today + datetime.timedelta(days=wiki.thresholds["due_soon_days"])
    records = []
    for page in wiki.pages():
        if page.meta is None or page.type != "task":
            continue
        record = task_record(page, today, closed)
        if _in_view(record, view, today, horizon, closed) and _matches(record, project, person, priority):
            records.append(record)
    records.sort(key=_sort_key)
    return records


def _in_view(record, view, today, horizon, closed):
    if view == "all":
        return True
    if view == "blocked":
        return record["status"] == "blocked"
    if record["status"] in closed:
        return False
    due = parse_date(record["due"])
    if view == "mine":
        return not record["delegated"]
    if view == "delegated":
        return record["delegated"]
    if view == "overdue":
        return record["overdue"]
    if view == "today":
        return due is not None and due <= today
    return due is not None and due <= horizon  # week


def _matches(record, project, person, priority):
    related = {norm(r) for r in record["related"]}
    if priority and record["priority"] != priority:
        return False
    if project and norm(project) not in related:
        return False
    if person:
        people = set(related)
        if record["owner"]:
            people.add(norm(record["owner"]))
        if norm(person) not in people:
            return False
    return True


def _sort_key(record):
    return (
        record["due"] is None,
        record["due"] or "",
        PRIORITY_RANK.get(record["priority"], 3),
        norm(record["title"]),
    )
