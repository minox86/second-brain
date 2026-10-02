# Second Brain (`sb`)

Plugin Claude Code che trasforma Claude Code nel pannello di controllo di una **wiki LLM** per il lavoro di management. Si inseriscono note, documenti e pagine Confluence; Claude le organizza in una wiki Markdown strutturata e collegata (compatibile con Obsidian), che poi si interroga.

Design: [`docs/superpowers/specs/2026-10-02-second-brain-core-design.md`](docs/superpowers/specs/2026-10-02-second-brain-core-design.md)

## Requisiti

- Claude Code
- Python 3.9 o superiore (`python3`) e git
- Opzionali: i connettori MCP Atlassian (Confluence, Jira) e Microsoft 365 (mail)

## Installazione

In Claude Code:

    /plugin marketplace add minox86/second-brain
    /plugin install sb@second-brain

## Creare una wiki

Crea (o clona vuota) una cartella per la wiki, aprici Claude Code ed esegui `/sb:init`. Un'intervista genera lo schema partendo dal preset Head of Engineering.

## Comandi

| Comando | Scopo |
|---|---|
| `/sb:status` | Cruscotto: cosa richiede attenzione |
| `/sb:put <input>` | Fa entrare testo, file, Confluence, Jira, mail, web |
| `/sb:sync [sorgente] [--check]` | Riallinea le sorgenti esterne cambiate |
| `/sb:ask <domanda>` | Risposta puntuale con citazioni |
| `/sb:prep <target>` | Briefing per 1:1, riunione, persona, progetto |
| `/sb:report <tipo>` | Sintesi: settimana, mese, rischi, carico, upward, delegati |
| `/sb:tasks [vista \| azione]` | Vede e gestisce i task |
| `/sb:lint [--fix]` | Manutenzione |
| `/sb:schema [azione]` | Evoluzione dello schema |

Tutti i comandi si attivano anche in linguaggio naturale.

## Sviluppo

    python3 -m unittest discover -s tests -v     # test del toolkit
    claude plugin validate . --strict            # manifest e skill
    claude --plugin-dir .                        # prova locale del plugin

Gli scenari di accettazione delle skill sono in [`tests/scenarios/README.md`](tests/scenarios/README.md).
