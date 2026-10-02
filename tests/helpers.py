"""Helper condivisi dai test del toolkit."""
import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "toolkit"))

from sb_core.cli import main  # noqa: E402


def run_cli(*argv):
    """Esegue la CLI in-process. Ritorna (exit_code, json_stdout | None, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main([str(a) for a in argv])
        except SystemExit as exc:  # argparse su errori d'uso o --help
            code = exc.code
    text = out.getvalue().strip()
    data = json.loads(text) if text.startswith("{") else None
    return code, data, err.getvalue()
