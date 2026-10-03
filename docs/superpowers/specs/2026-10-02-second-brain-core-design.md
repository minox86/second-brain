# Second Brain — Core: design

- **Data:** 2026-10-02
- **Stato:** proposta, in revisione
- **Ambito:** sotto-progetto 1 (Core) di 3

## 1. Obiettivo e contesto

Second Brain è un **plugin per Claude Code** che trasforma Claude Code nel pannello di controllo di un "secondo cervello" personale, pensato per le attività di management di un Head of Engineering.

Si basa sul pattern **LLM Wiki**: le sorgenti vengono ingerite e l'LLM mantiene una wiki strutturata e collegata, che poi consulta. L'evoluzione rispetto al pattern base è che la struttura dei contenuti ha una **semantica esplicita**, definita all'inizializzazione tramite un'intervista e fatta evolvere nel tempo.

**Criterio di successo:** nel lavoro quotidiano (1:1, riunioni, decisioni, persone, progetti, task) l'utente usa Claude Code come punto unico per mettere dentro e ritrovare informazioni, senza mantenere la struttura a mano.

### Scomposizione

| # | Sotto-progetto | Stato |
|---|---|---|
| 1 | **Core**: modello semantico, skill, toolkit, distribuzione | questo documento |
| 2 | Routine schedulate: sync periodico, lint periodico, status proattivo | ciclo successivo |
| 3 | Artefatti visuali, a partire dal task board | ciclo successivo |

Il Core espone le interfacce di cui 2 e 3 hanno bisogno (`sync --check`, `status`, `tasks list --json`) senza implementarne la logica.

### Decisioni prese

| Tema | Decisione |
|---|---|
| Riusabilità | Plugin distribuibile; ogni progetto è una **wiki separata** (repo dedicato) |
| Schema | **Generato da un'intervista** all'init, ispirandosi a un preset Head of Engineering |
| Sorgenti | Testo libero/dettato, file, contenuti via MCP (Confluence, Jira, M365), link web |
| Grezzo | **Ibrido**: si conserva il grezzo senza "casa" esterna; per le sorgenti esterne si tengono riferimento + sintesi |
| Custodia | Remote git per wiki, scelto all'init; **commit e push automatici** a ogni operazione |
| Task | Vivono **nella wiki**; tutti i campi sono opzionali e inferiti dall'LLM |
| Query | Puntuale, briefing, sintesi trasversali; briefing e sintesi **riarchiviati automaticamente** |
| Evoluzione schema | **Proposta dall'LLM**, applicata con migrazione dopo l'ok dell'utente |
| Manutenzione | Lint **su richiesta** nel Core (schedulato nel sotto-progetto 2) |
| Architettura | Skill + **toolkit deterministico** Python (solo standard library) |
| Piattaforma | Uso principale su macOS; wiki **compatibili con Obsidian** |
| KB esterna | Confluence e simili sono un **livello raw esterno**: autorevoli per i fatti, rielaborati nella struttura della wiki |

## 2. Architettura

### Principio

**LLM per la semantica, toolkit per la meccanica.** L'LLM capisce, smista, sintetizza, inferisce e propone. Il toolkit valida, indicizza, risolve nomi, interroga i task e applica le migrazioni. Il toolkit non chiama mai l'LLM, e l'LLM non fa mai a mano ciò che fa il toolkit.

### Repo `second-brain`: il plugin (nessun contenuto)

```
second-brain/
├── .claude-plugin/
│   ├── plugin.json            # manifest; nome plugin: "sb"
│   └── marketplace.json       # installazione via /plugin da questo repo
├── skills/
│   ├── init/   status/   put/   sync/
│   ├── ask/    prep/     report/
│   ├── tasks/  lint/     schema/
│   └── _shared/               # riferimenti comuni (regole, pipeline, formati)
├── toolkit/
│   └── sb.py                  # CLI deterministica
├── presets/
│   └── head-of-engineering/   # schema di ispirazione per l'intervista
└── tests/
    └── fixtures/              # wiki di esempio per i test
```

Le skill si invocano come `/sb:<skill>`.

### Una wiki: repo separato creato da `/sb:init`

```
<my-wiki>/
├── CLAUDE.md                  # marca la cartella come wiki; regole e puntatori
├── schema/
│   ├── VERSION                # versione del formato
│   ├── wiki.md                # opzionale: `name` della wiki (default: nome della cartella)
│   ├── layers.md              # semantica dei layer
│   ├── sources.md             # registro delle KB esterne
│   ├── proposals.md           # proposte di evoluzione: una checklist `- [ ] P<n> · …`
│   ├── types/<tipo>.md        # un file per tipo
│   ├── briefings/<tipo>.md    # template dei briefing
│   └── reports/<tipo>.md      # template dei report
├── knowledge/                 # layer statico
├── operations/                # layer operativo
├── outputs/
│   ├── briefings/
│   └── reports/
├── raw/YYYY/MM/               # grezzo conservato, immutabile
├── index.md                   # generato dal toolkit
├── .sb/backlinks.json         # generato dal toolkit
├── log.md                     # registro cronologico, append-only
└── .obsidian/                 # configurazione minima opzionale
```

### Flusso di ogni operazione di scrittura

1. Lavoro semantico dell'LLM.
2. Scrittura delle pagine.
3. `sb.py validate`, con correzione e ripetizione se servono.
4. `sb.py index`.
5. `sb.py log`.
6. `git commit` + `git push`.

## 3. Modello dei contenuti

### 3.1 Layer

Ogni tipo appartiene a un layer. I layer hanno una semantica di comportamento descritta in `schema/layers.md`:

- **knowledge**: conoscenza che cambia lentamente. Le pagine si *aggiornano e consolidano*: sezioni stabili, niente cronologia minuta. Il lint cerca contraddizioni.
- **operations**: eventi e item datati, con stato e ad alto ricambio. Le pagine si *creano, chiudono e archiviano*. Il lint cerca elementi stantii.

Le soglie temporali usate da `lint` e `status` stanno nel frontmatter di `layers.md`, con questi default: `stale_operations_days: 30`, `one_on_one_gap_days: 21`, `due_soon_days: 7`.

**Regola di propagazione:** un'informazione operativa che cambia la conoscenza stabile aggiorna anche la pagina knowledge corrispondente e la linka. Per esempio, una decisione presa in un meeting aggiorna la pagina del progetto.

### 3.2 Formato di una pagina

```markdown
---
type: person                # obbligatorio; deve esistere in schema/types/
title: Luca Bianchi         # obbligatorio
aliases: [Luca, LB]         # opzionale; usato da resolve e da Obsidian
created: 2026-10-02
updated: 2026-10-02
sources: [raw/2026/10/2026-10-02-1on1-luca, "jira:PLAT-123"]
# campi specifici del tipo
---
Corpo in Markdown con [[wikilink]].
Le affermazioni rilevanti citano la fonte. ^[raw/2026/10/2026-10-02-1on1-luca]
```

- **Nome del file = titolo** (`knowledge/people/Luca Bianchi.md`), perché Obsidian risolve i wikilink sul nome del file. Di conseguenza i titoli non possono contenere `\ / : * ? " < > | # ^ [ ]` e devono essere unici in tutta la wiki.
- **Wikilink** sempre verso il titolo canonico: `[[Luca Bianchi]]`. Per mostrare un alias si usa `[[Luca Bianchi|Luca]]`. Un link che punta a un alias viene risolto dal toolkit ma segnalato da validate come non canonico.
- **Riferimenti esterni** con prefisso: `confluence:<SPACE>/<pageId>`, `jira:<KEY>`, `mail:<id>`, `url:<url>`.
- **Frontmatter**: sottoinsieme ristretto di YAML (scalari, stringhe tra virgolette, liste inline o a blocco, date ISO, mappe di un livello nei file di schema). Lo legge il parser del toolkit.

### 3.3 Definizione di tipo (`schema/types/<tipo>.md`)

```markdown
---
name: person
layer: knowledge
folder: knowledge/people
fields:
  role:       {kind: string}
  team:       {kind: link, to: team}
  reports_to: {kind: link, to: person}
  status:     {kind: enum, values: [active, left], default: active}
required: []
---
# Person
Una persona con cui lavori: report, peer, stakeholder, contatto di un fornitore.
Crea una pagina quando… Non crearla quando… Aggiorna la sezione "Note" quando…
```

- Il **frontmatter** serve al toolkit. `kind` ∈ `string | text | date | number | bool | enum | link | list`; `list` accetta `of: <kind>`.
- La **prosa** serve all'LLM: quando usare il tipo, come strutturare il corpo, cosa escludere.
- Un campo `status` di tipo `enum` può dichiarare `closed: [...]`, cioè i valori che chiudono l'item. Lint e status lo usano per capire cosa è ancora aperto; il default è `[done, dropped]`.
- I campi comuni (`type`, `title`, `aliases`, `created`, `updated`, `sources`, `external`, `version`, `synced`, `authority`) sono impliciti per tutti i tipi.

### 3.4 Task

Ogni task è una pagina in `operations/tasks/`.

```markdown
---
type: task
title: Chiedere a Luca la stima per la migrazione DB
status: todo                # todo | doing | blocked | done | dropped
owner: "[[Luca Bianchi]]"   # assente = l'utente; diverso = delegato da monitorare
due: 2026-10-09
priority: high              # low | medium | high
related: ["[[Migrazione DB]]", "[[2026-10-02 1on1 Luca]]"]
created: 2026-10-02
sources: [raw/2026/10/2026-10-02-1on1-luca]
---
Contesto breve e cronologia degli aggiornamenti.
```

- Tutti i campi tranne `type` e `title` sono opzionali. `status` assente equivale a `todo`.
- I campi sono inferiti dall'LLM. Se un campo non si può inferire con ragionevole sicurezza, viene **omesso**, mai inventato.

### 3.5 Grezzo (`raw/`)

- Si conserva per dettati, trascrizioni e file locali: un `.md` per ingestione con frontmatter `kind` (`dictation | transcript | file | excerpt`), `captured` e `origin`, più il contenuto originale intatto.
- I file binari (es. PDF) vengono copiati accanto al loro `.md`, che contiene il testo estratto.
- `raw/` è **immutabile**: nessuna skill lo modifica dopo la cattura.
- Per le sorgenti esterne il grezzo **non** si salva: si usa una source-note (§3.6).

### 3.6 Sorgenti e KB esterne

**Principio:** le KB esterne (Confluence in primis, ma anche Jira e il web) sono un **livello raw esterno**.

| | Fonte di verità |
|---|---|
| Fatti documentati da altri (processi, architetture, policy) | La sorgente esterna |
| Struttura, collegamenti, sintesi, punto di vista dell'utente, layer operations | La wiki |

**Registro (`schema/sources.md`)**: il frontmatter contiene la mappa `sources` (chiave = id della sorgente), il corpo descrive in prosa a cosa serve ogni sorgente.

```yaml
---
sources:
  conf-eng: {system: confluence, scope: ENG, covers: [process, system], stale_after_days: 30}
  jira-plat: {system: jira, scope: PLAT, covers: [project], stale_after_days: 14}
---
```

`scope` è il prefisso alfanumerico del riferimento `external`: lo spazio in `confluence:ENG/123`, il progetto in `jira:PLAT-123`. Le source-note `url:` e `mail:` non diventano mai stantie, perché sono catture una tantum. Quelle di sistemi senza un registro corrispondente usano una soglia di 30 giorni.

**Source-note**, tipo `source-note` in `knowledge/sources/`: una per ogni documento esterno ingerito.

```yaml
---
type: source-note
title: "Confluence · Incident Management"
external: "confluence:ENG/123456789"
version: 42                    # versione o lastModified della sorgente
synced: 2026-10-02
---
Sintesi del documento, con link alle pagine tipizzate che ne derivano.
```

**Regole:**

1. **Propagazione.** L'ingestione di un documento esterno crea o aggiorna la source-note e propaga i fatti nelle pagine tipizzate (`process`, `system`, `project`…) citando `^[confluence:ENG/123456789]`.
2. **Re-ingest.** Si rielabora solo ciò che è cambiato, cioè quando la versione è diversa o `synced` supera la soglia. Nel Core avviene su richiesta tramite `/sb:sync`.
3. **Conflitti.** In caso di contrasto vince la sorgente esterna. Se il fatto contraddetto proveniva da una nota dell'utente, non si sovrascrive in silenzio: lo si segnala.
4. **Opinioni dell'utente.** Le opinioni e valutazioni dell'utente, cioè contenuti non derivati da una sorgente, non vengono mai toccate dal re-ingest.
5. **Migrazione una tantum.** Con `authority: migrated` sulla source-note la wiki diventa fonte di verità e la sorgente non viene più re-ingerita. Si usa per contenuti dell'utente da portare dentro.

### 3.7 Preset `head-of-engineering`

È un punto di partenza per l'intervista, non uno schema imposto.

| Layer | Tipo | Cartella |
|---|---|---|
| knowledge | `person` | `knowledge/people` |
| knowledge | `team` | `knowledge/teams` |
| knowledge | `project` (scopo, architettura, stakeholder) | `knowledge/projects` |
| knowledge | `system` (servizi, piattaforme) | `knowledge/systems` |
| knowledge | `process` (rituali, policy, playbook) | `knowledge/processes` |
| knowledge | `topic` (hiring, budget, tech debt…) | `knowledge/topics` |
| knowledge | `vendor` | `knowledge/vendors` |
| knowledge | `source-note` | `knowledge/sources` |
| operations | `task` | `operations/tasks` |
| operations | `one-on-one` | `operations/one-on-ones` |
| operations | `meeting` | `operations/meetings` |
| operations | `decision` (ADR leggero) | `operations/decisions` |
| operations | `goal` (OKR) | `operations/goals` |
| operations | `risk` | `operations/risks` |

`source-note` e `task` sono **tipi di sistema**: il toolkit dipende dalla loro presenza e dai loro campi base. L'intervista può estenderli ma non rimuoverli.

Il preset include anche template di briefing (`one-on-one`, `meeting`, `person`, `project`) e di report (`week`, `month`, `risks`, `load`, `upward`, `delegated`).

## 4. Comandi utente

Ogni comando ha due ingressi equivalenti: lo slash command con argomenti e il linguaggio naturale, che attiva la skill tramite la sua descrizione. Tutti operano sulla wiki della **directory corrente o di una sua cartella madre**, riconosciuta dalla presenza di `schema/VERSION`. Fuori da una wiki, ogni comando tranne `init` si ferma e propone `/sb:init`.

| Comando | Scopo |
|---|---|
| `/sb:init [path]` | Crea una wiki |
| `/sb:status` | Cruscotto di ciò che richiede attenzione |
| `/sb:put <input>` | Fa entrare contenuti |
| `/sb:sync [sorgente]` | Re-ingest delle sorgenti esterne cambiate o stantie |
| `/sb:ask <domanda>` | Domanda puntuale con citazioni |
| `/sb:prep <target>` | Briefing di preparazione (archiviato) |
| `/sb:report <tipo>` | Sintesi trasversale (archiviata) |
| `/sb:tasks [vista \| azione]` | Vedere e gestire i task |
| `/sb:lint [--fix]` | Manutenzione |
| `/sb:schema [azione]` | Evoluzione dello schema |

### `/sb:init [path]`

1. **Intervista**, una domanda alla volta: ruolo e contesto, team e riporti, ritmi (1:1, rituali), KB esterne (spazi Confluence, progetti Jira), cosa serve ritrovare più spesso, remote git.
2. **Proposta di schema**, derivata dal preset e adattata alle risposte. Viene presentata come elenco di tipi per layer, con sorgenti e template, e richiede conferma.
3. **Scaffold** tramite `sb.py scaffold`.
4. **Seed opzionale** delle pagine `person`/`team` emerse dall'intervista.
5. `git init`, configurazione del remote, primo commit e push.

Se `path` esiste e non è vuoto, si ferma e chiede.

### `/sb:status`

Cruscotto di 10–15 righe:
- task scaduti o in scadenza entro `due_soon_days`;
- delegati in ritardo;
- persone con 1:1 senza note da oltre `one_on_one_gap_days` (§3.1), calcolate sulle pagine di tipo `one-on-one` tramite i campi `with` e `date`;
- sorgenti stantie;
- proposte di schema pendenti;
- conteggio delle issue di lint;
- stato git (modifiche non committate, push falliti).

Solo lettura.

### `/sb:put <input> [--as <tipo>] [--plan]`

**`<input>` riconosciuto automaticamente:**
- testo libero (multi-riga, incollato o dettato);
- percorso di un file o di una cartella (lotto);
- URL web;
- URL Confluence o `confluence:<SPACE>/<id>`;
- `jira:<KEY>`, oppure JQL tra virgolette (`"jira: project = PLAT AND updated >= -7d"`);
- `mail:` più un criterio di ricerca.

Senza argomenti chiede cosa ingerire.

**Opzioni:**
- `--as <tipo>` forza l'interpretazione principale (es. `one-on-one`). Senza, la deduce l'LLM.
- `--plan` mostra sempre il piano delle modifiche prima di scrivere. Di default il piano si mostra solo in caso di ambiguità: entità sconosciuta simile a una esistente, tipo incerto, conflitto con una sorgente.

**Pipeline:**
1. **Cattura:** `raw/` oppure source-note (§3.5, §3.6).
2. **Analisi:** riconoscimento delle entità tramite `sb.py resolve`; estrazione di fatti, decisioni, task e rischi.
3. **Piano:** pagine da creare o aggiornare.
4. **Scrittura:** knowledge consolidata, operations create, citazioni, campi inferiti.
5. **Chiusura:** flusso standard (§2).
6. **Riepilogo** di 3–6 righe: creato, aggiornato, task estratti, dubbi.

Esempi:
- `/sb:put --as one-on-one Luca: vuole passare a staff, preoccupato per on-call…`
- `/sb:put confluence:ENG/123456789`
- `/sb:put ~/Downloads/qbr-q3.pdf`

### `/sb:sync [<source-id> | <pagina> | --all] [--check]`

- **Senza argomenti:** usa `sb.py sources stale` e verifica le versioni via MCP; elenca ciò che è cambiato o stantio e chiede cosa rielaborare.
- **`<source-id>`:** rielabora ciò che è cambiato in quella sorgente. **`--all`:** rielabora tutto ciò che è cambiato.
- **`--check`:** solo report, nessuna scrittura. È l'aggancio per il sotto-progetto 2.

Il re-ingest segue le regole di §3.6.

### `/sb:ask <domanda> [--live]`

- Risponde dalla wiki con citazioni alle pagine e alle sorgenti.
- Va live via MCP solo se la wiki non basta; `--live` lo forza.
- Non archivia. Su richiesta esplicita ("salvala") la risposta diventa un output in `outputs/reports/`.

### `/sb:prep <target> [--for <data>]`

- `<target>` viene risolto contro la wiki:
  - persona → briefing 1:1;
  - meeting o ricorrenza → briefing di riunione;
  - progetto o team → stato.
- Il template viene da `schema/briefings/`. Contenuti tipici: stato, task aperti in entrambe le direzioni, temi ricorrenti, impegni presi, novità dalle sorgenti.
- **Archiviazione automatica** in `outputs/briefings/Briefing YYYY-MM-DD <target>.md` (con frontmatter `type: briefing`, `about`, `for`), poi flusso standard. `briefing` e `report` sono tipi predefiniti del toolkit e non stanno in `schema/types/`.

Esempi: `/sb:prep Luca` · `/sb:prep "weekly platform" --for domani`

### `/sb:report <tipo> [--scope <entità>] [--period <periodo>]`

- Tipi da `schema/reports/`. Il preset include `week`, `month`, `risks`, `load`, `upward`, `delegated`.
- **Archiviazione automatica** in `outputs/reports/Report YYYY-MM-DD <tipo>[ <scope>].md` (frontmatter `type: report`, `kind`, `scope`, `period`), poi flusso standard.

Esempi: `/sb:report week` · `/sb:report risks --scope "[[Platform]]"` · `/sb:report upward --period 2026-09`

### `/sb:tasks [vista] [filtri]` · `/sb:tasks <azione> …`

**Viste:** `mine` (default), `delegated`, `overdue`, `today`, `week`, `blocked`, `all`.
**Filtri:** `--project`, `--person`, `--priority`.

**Azioni:**
- `add <testo>`: i campi vengono inferiti;
- `done <task>`;
- `drop <task>`;
- `update <task> <modifica in linguaggio naturale>`.

`<task>` si risolve per titolo approssimato; se è ambiguo, chiede. L'output è una tabella compatta nel terminale. Le azioni eseguono il flusso standard.

### `/sb:lint [--fix] [--only structural|semantic]`

- **Strutturale** (`sb.py lint`): link rotti, pagine orfane, campi non validi, source-note stantie, task scaduti, item operations senza aggiornamenti da oltre `stale_operations_days`.
- **Semantico** (LLM): duplicati probabili, contraddizioni tra pagine, fatti superati dalle sorgenti, pagine knowledge da consolidare. Durante l'analisi registra in `schema/proposals.md` i segnali di evoluzione dello schema.
- **Default:** solo report. **`--fix`:** applica subito le correzioni meccaniche e propone quelle semantiche una alla volta.

### `/sb:schema [proposals | add <tipo> | change <tipo> <modifica> | apply <id>]`

- **Senza argomenti:** sintesi dello schema (tipi per layer) e numero di proposte pendenti.
- **`proposals`:** presenta i segnali raccolti da put e lint come proposte concrete, cioè diff dello schema + piano di migrazione.
- **`add` / `change`:** modifica richiesta direttamente dall'utente.
- **`apply <id>`:** dopo conferma, aggiorna lo schema, genera il piano di migrazione, esegue `sb.py migrate`, valida e fa commit dedicato.

## 5. Toolkit `sb.py`

Python ≥ 3.9 (il Python 3 di macOS Command Line Tools è 3.9), solo standard library. Un solo punto d'ingresso eseguibile, `toolkit/sb.py`, con i moduli nel package `toolkit/sb_core/`. Ogni comando:
- restituisce **JSON su stdout**;
- scrive su stderr la diagnostica leggibile;
- usa codici di uscita `0` (ok), `1` (problemi trovati), `2` (errore d'uso o di ambiente).

Ogni comando accetta `--wiki <path>`; di default usa la directory corrente.

| Comando | Comportamento |
|---|---|
| `validate [paths…]` | Valida frontmatter e schema: tipo esistente, campi richiesti, `kind`, valori `enum`, target dei `link` esistenti e del tipo giusto, prefisso di `external` registrato in `sources.md`, file nella cartella del tipo |
| `index` | Rigenera `index.md` (per layer e tipo, con titolo e data) e `.sb/backlinks.json` |
| `resolve <nome> [--type <tipo>]` | Candidati per titolo e alias, con punteggio (esatto > alias > fuzzy) |
| `tasks list [--view …] [filtri] [--json]` | Query sui task; `--json` è il **contratto per gli artefatti** |
| `sources stale` | Source-note con `synced` oltre la soglia della propria sorgente |
| `lint` | Controlli strutturali di §4 `/sb:lint` |
| `migrate <piano.json>` | Applica una migrazione: sposta file, rinomina o rimappa campi, cambia tipo, riscrive i wikilink; `--dry-run` disponibile |
| `log <messaggio> [--op <operazione>]` | Aggiunge `- YYYY-MM-DD HH:MM · <op> · <messaggio>` a `log.md` |
| `scaffold <schema-dir> <path>` | Crea la wiki da una cartella `schema/` approvata (stesso formato di §2, così il preset è già una cartella schema) |
| `status` | Dati del cruscotto di `/sb:status`: task scaduti e in scadenza, delegati in ritardo, 1:1 oltre soglia, sorgenti stantie, proposte aperte, conteggio lint |

### Contratto `tasks list --json`

```json
{
  "generated": "2026-10-02T09:00:00",
  "tasks": [
    {
      "path": "operations/tasks/chiedere-a-luca-la-stima.md",
      "title": "Chiedere a Luca la stima per la migrazione DB",
      "status": "todo",
      "owner": "Luca Bianchi",
      "delegated": true,
      "due": "2026-10-09",
      "overdue": false,
      "priority": "high",
      "related": ["Migrazione DB", "2026-10-02 1on1 Luca"],
      "created": "2026-10-02"
    }
  ]
}
```

I campi assenti nel frontmatter sono `null`, tranne `status`, che di default vale `"todo"`. `owner` è `null` per i task dell'utente.

### Versionamento del formato

`schema/VERSION` contiene la versione del formato della wiki. Il toolkit rifiuta di operare (exit `2`) su wiki con versione maggiore della propria. Su versioni minori indica la migrazione di formato da eseguire.

## 6. Regole comuni (`CLAUDE.md` della wiki)

- Nessun fatto senza fonte; nessun campo inventato.
- Mai modificare `raw/`.
- Le opinioni dell'utente non si sovrascrivono durante un re-ingest.
- Ogni operazione di scrittura termina con il flusso standard (§2).
- Le operazioni distruttive (migrate, merge di duplicati, cancellazioni) richiedono conferma e un commit dedicato.

## 7. Gestione errori

| Situazione | Comportamento |
|---|---|
| `validate` fallisce dopo una scrittura | Correzione e nuovo tentativo (max 2). Poi commit di quanto è valido, segnalazione delle pagine problematiche, annotazione in `log.md`. Mai lasciare modifiche senza commit |
| MCP non disponibile | `put`/`sync` lo dichiarano e si fermano su quella sorgente. `ask` risponde dalla wiki dichiarando la fonte live irraggiungibile. Mai dati inventati |
| Push fallito | Il commit locale resta; `status` lo segnala; il push successivo recupera |
| Entità ambigua | Domanda puntuale; la risposta viene salvata come `alias` per le volte successive |
| Wiki non trovata o versione incompatibile | Arresto con messaggio e indicazione dell'azione (`/sb:init` o migrazione) |

## 8. Test

- **Toolkit:** unit test con `unittest` su wiki temporanee costruite dai test. Coprono parser del frontmatter, `validate`, `resolve`, `tasks list` (incluso il contratto JSON), `sources stale`, `lint`, `migrate`, `scaffold`. Sviluppo in TDD.
- **Skill:** wiki di esempio `tests/fixtures/sample-wiki` più scenari di accettazione in `tests/scenarios/`, nella forma "input → aspettative verificabili con il toolkit". Esempio: dopo `/sb:put` di un dettato di 1:1 esiste una pagina `one-on-one` linkata alla persona e almeno un task con `owner` valorizzato; `sb.py validate` esce con `0`. Esecuzione manuale o con `claude -p`.

## 9. Fuori scope

- Routine schedulate (sotto-progetto 2): `sync --check` periodico, lint periodico, status proattivo, fetch automatico.
- Artefatti visuali (sotto-progetto 3): task board su `tasks list --json`.
- Ricerca semantica o embedding, server MCP della wiki.
- Uso multi-utente o collaborativo di una stessa wiki.
