"""Source-note da riallineare con le sorgenti esterne registrate."""
import re

from .wiki import DEFAULT_SOURCE_STALE_DAYS, parse_date

ONE_OFF_SYSTEMS = ("url", "mail")
_SCOPE = re.compile(r"[A-Za-z0-9_]+")


def parse_external(ref):
    system, _, rest = ref.partition(":")
    match = _SCOPE.match(rest)
    return system, (match.group(0) if match else None)


def registry_entry(wiki, system, scope):
    fallback = (None, None)
    for source_id, entry in sorted(wiki.sources.items()):
        if entry.get("system") != system:
            continue
        entry_scope = entry.get("scope")
        if entry_scope is not None and scope is not None and str(entry_scope) == scope:
            return source_id, entry
        if entry_scope is None and fallback == (None, None):
            fallback = (source_id, entry)
    return fallback


def stale_sources(wiki, today):
    results = []
    for page in wiki.pages():
        if page.meta is None or page.type != "source-note":
            continue
        meta = page.meta
        if meta.get("authority") == "migrated":
            continue
        external = meta.get("external") if isinstance(meta.get("external"), str) else None
        system, scope = parse_external(external) if external else (None, None)
        if system in ONE_OFF_SYSTEMS:
            continue
        source_id, entry = registry_entry(wiki, system, scope) if system else (None, None)
        threshold = (entry or {}).get("stale_after_days")
        if not isinstance(threshold, int) or isinstance(threshold, bool):
            threshold = DEFAULT_SOURCE_STALE_DAYS
        synced = parse_date(meta.get("synced"))
        if synced is None:
            reason, age = "never-synced", None
        else:
            age = (today - synced).days
            if age <= threshold:
                continue
            reason = "expired"
        results.append({
            "path": page.path, "title": page.title, "external": external, "source_id": source_id,
            "synced": synced.isoformat() if synced else None, "age_days": age,
            "threshold_days": threshold, "reason": reason,
        })
    results.sort(key=lambda r: (r["age_days"] is not None, -(r["age_days"] or 0), r["path"]))
    return results
