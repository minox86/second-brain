"""Interfaccia a riga di comando: argomenti, dispatch, output JSON, exit code."""
import argparse
import datetime
import json
import sys
from collections import Counter

from . import FORMAT_VERSION, __version__
from .errors import SbError, UsageError
from .index import write_index
from .links import link_target_name
from .lint import lint
from .log import append_log
from .migrate import load_plan, migrate
from .resolve import resolve
from .sources import stale_sources
from .status import status
from .tasks import VIEWS, list_tasks
from .validate import validate
from .wiki import Wiki, find_root


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result, code = args.handler(args)
    except SbError as exc:
        print(f"sb: {exc}", file=sys.stderr)
        _emit({"error": str(exc)})
        return 2
    _emit(result)
    return code


def _emit(data):
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _today(args):
    value = getattr(args, "today", None)
    if not value:
        return datetime.date.today()
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise UsageError("--today deve essere nel formato AAAA-MM-GG")


def build_parser():
    parser = argparse.ArgumentParser(prog="sb", description="Toolkit deterministico di Second Brain")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--wiki", default=".", help="cartella della wiki o una sua sottocartella (default: .)")
    common.add_argument("--today", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", metavar="<comando>")
    sub.required = True
    for register in COMMANDS:
        register(sub, common)
    return parser


def _add_version(sub, common):
    p = sub.add_parser("version", parents=[common], help="versione del toolkit")
    p.set_defaults(handler=cmd_version)


def cmd_version(args):
    try:
        root = str(find_root(args.wiki))
    except SbError:
        root = None
    return {"toolkit": __version__, "format": FORMAT_VERSION, "wiki": root}, 0


def _wiki(args):
    return Wiki(args.wiki)


def _add_validate(sub, common):
    p = sub.add_parser("validate", parents=[common], help="valida le pagine contro lo schema")
    p.add_argument("paths", nargs="*", help="pagine da validare (default: tutte)")
    p.set_defaults(handler=cmd_validate)


def cmd_validate(args):
    wiki = _wiki(args)
    issues = validate(wiki, args.paths)
    errors = [i for i in issues if i.severity == "error"]
    checked = len(args.paths) if args.paths else len(wiki.pages())
    return {"ok": not errors, "checked": checked, "issues": [i.to_dict() for i in issues]}, 1 if errors else 0


def _add_index(sub, common):
    p = sub.add_parser("index", parents=[common], help="rigenera index.md e .sb/backlinks.json")
    p.set_defaults(handler=cmd_index)


def cmd_index(args):
    return write_index(_wiki(args)), 0


def _add_resolve(sub, common):
    p = sub.add_parser("resolve", parents=[common], help="pagine candidate per un nome")
    p.add_argument("name")
    p.add_argument("--type", dest="type_name", help="limita a un tipo di pagina")
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(handler=cmd_resolve)


def cmd_resolve(args):
    name = link_target_name(args.name)
    if not name:
        raise UsageError("il nome da risolvere è vuoto")
    return resolve(_wiki(args), name, args.type_name, args.limit), 0


def _add_tasks(sub, common):
    p = sub.add_parser("tasks", help="query sui task")
    tsub = p.add_subparsers(dest="tasks_command", metavar="<azione>")
    tsub.required = True
    lp = tsub.add_parser("list", parents=[common], help="task di una vista")
    lp.add_argument("--view", choices=VIEWS, default="mine")
    lp.add_argument("--project", help="titolo del progetto in 'related'")
    lp.add_argument("--person", help="persona come owner o in 'related'")
    lp.add_argument("--priority", choices=("low", "medium", "high"))
    lp.add_argument("--json", action="store_true", help="output JSON (sempre attivo)")
    lp.set_defaults(handler=cmd_tasks_list)


def cmd_tasks_list(args):
    records = list_tasks(
        _wiki(args), view=args.view,
        project=link_target_name(args.project), person=link_target_name(args.person),
        priority=args.priority, today=_today(args),
    )
    generated = datetime.datetime.now().isoformat(timespec="seconds")
    return {"generated": generated, "view": args.view, "tasks": records}, 0


def _add_sources(sub, common):
    p = sub.add_parser("sources", help="sorgenti esterne")
    ssub = p.add_subparsers(dest="sources_command", metavar="<azione>")
    ssub.required = True
    sp = ssub.add_parser("stale", parents=[common], help="source-note da riallineare")
    sp.set_defaults(handler=cmd_sources_stale)


def cmd_sources_stale(args):
    return {"stale": stale_sources(_wiki(args), _today(args))}, 0


def _add_log(sub, common):
    p = sub.add_parser("log", parents=[common], help="aggiunge una riga a log.md")
    p.add_argument("message")
    p.add_argument("--op", default="note", help="nome dell'operazione (put, sync, …)")
    p.set_defaults(handler=cmd_log)


def cmd_log(args):
    wiki = _wiki(args)
    return append_log(wiki.root, args.message, args.op), 0


def _add_lint(sub, common):
    p = sub.add_parser("lint", parents=[common], help="controlli strutturali della wiki")
    p.set_defaults(handler=cmd_lint)


def cmd_lint(args):
    issues = lint(_wiki(args), _today(args))
    summary = dict(sorted(Counter(i.code for i in issues).items()))
    return {"ok": not issues, "summary": summary, "issues": [i.to_dict() for i in issues]}, 1 if issues else 0


def _add_status(sub, common):
    p = sub.add_parser("status", parents=[common], help="dati del cruscotto")
    p.set_defaults(handler=cmd_status)


def cmd_status(args):
    return status(_wiki(args), _today(args)), 0


def _add_migrate(sub, common):
    p = sub.add_parser("migrate", parents=[common], help="applica un piano di migrazione JSON")
    p.add_argument("plan", help="file JSON con {\"ops\": [...]}")
    p.add_argument("--dry-run", action="store_true", help="mostra le modifiche senza scrivere")
    p.set_defaults(handler=cmd_migrate)


def cmd_migrate(args):
    return migrate(_wiki(args), load_plan(args.plan), dry_run=args.dry_run), 0


COMMANDS = [_add_version, _add_validate, _add_index, _add_resolve, _add_tasks, _add_sources, _add_log, _add_lint, _add_status, _add_migrate]
