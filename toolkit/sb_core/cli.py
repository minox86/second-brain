"""Interfaccia a riga di comando: argomenti, dispatch, output JSON, exit code."""
import argparse
import datetime
import json
import sys

from . import FORMAT_VERSION, __version__
from .errors import SbError, UsageError
from .resolve import resolve
from .links import link_target_name
from .index import write_index
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


COMMANDS = [_add_version, _add_validate, _add_index, _add_resolve]
