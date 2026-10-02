"""Interfaccia a riga di comando: argomenti, dispatch, output JSON, exit code."""
import argparse
import datetime
import json
import sys

from . import FORMAT_VERSION, __version__
from .errors import SbError, UsageError


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
    return {"toolkit": __version__, "format": FORMAT_VERSION}, 0


COMMANDS = [_add_version]
