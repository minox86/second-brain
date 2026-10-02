"""Interfaccia a riga di comando: argomenti, dispatch, output JSON, exit code."""
import argparse
import datetime
import json
import os
import sys
import traceback
from collections import Counter

from . import FORMAT_VERSION, __version__
from .board_api import Board
from .board_server import run as run_board
from .errors import SbError, UsageError
from .index import write_index
from .links import link_target_name
from .lint import lint
from .log import append_log
from .migrate import load_plan, migrate
from .resolve import resolve
from .scaffold import scaffold
from .sources import stale_sources
from .status import status
from .tasks import VIEWS, list_tasks
from .validate import _relative, validate
from .wiki import Wiki, find_root


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result, code = args.handler(args)
    except SbError as exc:
        print(f"sb: {exc}", file=sys.stderr)
        _emit(getattr(exc, "payload", None) or {"error": str(exc)})
        return 2
    except Exception as exc:  # errore inatteso: resta nel contratto JSON + exit 2
        traceback.print_exc(file=sys.stderr)
        _emit({"error": f"errore interno: {type(exc).__name__}: {exc}"})
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
    common.add_argument("--wiki", default=None,
                        help="cartella della wiki o una sua sottocartella (default: $SB_WIKI, poi .)")
    common.add_argument("--today", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", metavar="<comando>")
    sub.required = True
    for register in COMMANDS:
        register(sub, common)
    return parser


def _add_version(sub, common):
    p = sub.add_parser("version", parents=[common], help="versione del toolkit")
    p.set_defaults(handler=lambda args: cmd_version(args))


def _wiki_path(args):
    return getattr(args, "wiki", None) or os.environ.get("SB_WIKI") or "."


def cmd_version(args):
    try:
        root = str(find_root(_wiki_path(args)))
    except SbError:
        root = None
    return {"toolkit": __version__, "format": FORMAT_VERSION, "wiki": root}, 0


def _wiki(args):
    return Wiki(_wiki_path(args))


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

    ap = tsub.add_parser("add", parents=[common], help="crea un task con campi espliciti")
    ap.add_argument("--title", required=True)
    ap.add_argument("--status")
    ap.add_argument("--owner", help="titolo di una pagina person")
    ap.add_argument("--due", help="AAAA-MM-GG")
    ap.add_argument("--priority")
    ap.add_argument("--related", action="append", default=[], help="titolo collegato (ripetibile)")
    ap.add_argument("--note")
    ap.set_defaults(handler=cmd_tasks_add)

    up = tsub.add_parser("update", parents=[common], help="modifica un task")
    up.add_argument("path", help="percorso del task")
    up.add_argument("--set", dest="sets", action="append", default=[], metavar="CAMPO=VALORE")
    up.add_argument("--unset", action="append", default=[], metavar="CAMPO")
    up.add_argument("--note")
    up.add_argument("--etag", help="rifiuta la modifica se il file è cambiato")
    up.set_defaults(handler=cmd_tasks_update)


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


def _add_scaffold(sub, common):
    p = sub.add_parser("scaffold", help="crea una nuova wiki da una cartella schema")
    p.add_argument("schema_dir", help="cartella schema (es. presets/head-of-engineering)")
    p.add_argument("target", help="cartella della nuova wiki (vuota o con solo .git)")
    p.set_defaults(handler=cmd_scaffold)


def cmd_scaffold(args):
    return scaffold(args.schema_dir, args.target), 0


def _board(args):
    today = _today(args) if getattr(args, "today", None) else None
    return Board(_wiki_path(args), today=(lambda: today) if today else None)


def _with_push(board, result):
    pushed = None
    if result["committed"] and board.git.has_remote():
        pushed, _ = board.git.push()
    return dict(result, pushed=pushed)


def cmd_tasks_add(args):
    board = _board(args)
    data = {"title": args.title, "status": args.status, "owner": args.owner, "due": args.due,
            "priority": args.priority, "related": args.related, "note": args.note}
    return _with_push(board, board.create(data)), 0


def cmd_tasks_update(args):
    board = _board(args)
    changes = {}
    for item in args.sets:
        key, sep, value = item.partition("=")
        if not sep or not key.strip():
            raise UsageError(f"--set vuole CAMPO=VALORE, non '{item}'")
        key = key.strip()
        changes[key] = [v.strip() for v in value.split(",") if v.strip()] if key == "related" else value.strip()
    for key in args.unset:
        changes[key.strip()] = None
    rel = _relative(board.wiki, args.path)
    result = board.update({"path": rel, "etag": args.etag, "set": changes, "note": args.note})
    return _with_push(board, result), 0


def _add_board(sub, common):
    p = sub.add_parser("board", parents=[common], help="avvia la board dei task nel browser")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-open", action="store_true", help="non aprire il browser")
    p.set_defaults(handler=cmd_board)


def cmd_board(args):
    board = _board(args)
    return run_board(board, port=args.port, open_browser=not args.no_open), 0


COMMANDS = [_add_version, _add_validate, _add_index, _add_resolve, _add_tasks, _add_sources, _add_log, _add_lint, _add_status, _add_migrate, _add_scaffold, _add_board]
