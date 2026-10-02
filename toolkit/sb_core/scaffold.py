"""Creazione di una nuova wiki a partire da una cartella schema (es. un preset)."""
import json
import shutil
from pathlib import Path

from . import FORMAT_VERSION
from .errors import WikiError
from .index import write_index
from .log import LOG_HEADER
from .wiki import Wiki, load_types

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "wiki"
IGNORABLE = (".git", ".DS_Store")
GITIGNORE = ".sb/\n.obsidian/workspace*.json\n.DS_Store\n"
OBSIDIAN_APP = {
    "newLinkFormat": "shortest",
    "useMarkdownLinks": False,
    "alwaysUpdateLinks": True,
    "userIgnoreFilters": ["raw/", "schema/"],
}
PROPOSALS_HEADER = (
    "# Proposte di schema\n\n"
    "Una proposta per voce: `- [ ] P<n> · <titolo>` con sotto-voci `- segnale:` e `- proposta:`.\n"
    "`- [x]` = applicata, `- [-]` = scartata (con il motivo).\n\n"
)


def scaffold(schema_dir, target, template_dir=TEMPLATE_DIR):
    schema_dir, target = Path(schema_dir), Path(target)
    version_file = schema_dir / "VERSION"
    if not version_file.is_file():
        raise WikiError(f"{schema_dir} non è una cartella schema (manca VERSION)")
    if version_file.read_text(encoding="utf-8").strip() != str(FORMAT_VERSION):
        raise WikiError(f"lo schema deve essere in formato {FORMAT_VERSION}")
    types = load_types(schema_dir)
    if target.exists() and any(p.name not in IGNORABLE for p in target.iterdir()):
        raise WikiError(f"{target} esiste e non è vuota: scegli un'altra cartella")
    template = Path(template_dir) / "CLAUDE.md"
    if not template.is_file():
        raise WikiError(f"template mancante: {template}")

    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(schema_dir), str(target / "schema"))
    proposals = target / "schema" / "proposals.md"
    if not proposals.exists():
        proposals.write_text(PROPOSALS_HEADER, encoding="utf-8")
    folders = sorted({t.folder for t in types.values()} | {"raw"})
    for folder in folders:
        directory = target / folder
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ".gitkeep").write_text("", encoding="utf-8")
    shutil.copyfile(str(template), str(target / "CLAUDE.md"))
    (target / "log.md").write_text(LOG_HEADER, encoding="utf-8")
    (target / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (target / ".obsidian").mkdir(exist_ok=True)
    (target / ".obsidian" / "app.json").write_text(json.dumps(OBSIDIAN_APP, indent=2) + "\n", encoding="utf-8")
    write_index(Wiki(target))
    return {"path": str(target.resolve()), "types": sorted(types), "folders": folders}
