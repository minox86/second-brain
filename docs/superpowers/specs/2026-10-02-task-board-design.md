# Task Board: design

- **Data:** 2026-10-02
- **Stato:** approvato in brainstorming, in revisione
- **Ambito:** sotto-progetto 3 (artefatti visuali), primo artefatto: la board dei task
- **Riferimento visivo:** tavola "Second Brain Task Board" (artefatto claude.ai, versione 3)
- **Dipende da:** `docs/superpowers/specs/2026-10-02-second-brain-core-design.md`

## 1. Obiettivo

Una board visuale per i task della wiki, per i casi d'uso in cui la conversazione è scomoda:

- **A: vedere a colpo d'occhio** lo stato dei task;
- **B: triage rapido** (chiudere, spostare, cambiare scadenza o priorità con un clic);
- **C: seguire i delegati** per persona;
- **D: filtrare e cercare**;
- **E: creare task al volo** con campi espliciti, senza LLM.

Si usa **solo dal Mac**, accanto a Claude Code; telefono e accesso remoto sono fuori scope. La wiki resta l'unica fonte di verità: ogni modifica fatta dalla board passa dal toolkit, con validazione, log e commit.

## 2. Architettura

Server HTTP locale nel toolkit, scritto con la sola standard library, più una pagina HTML/JS servita dal plugin, senza build.

```
toolkit/sb_core/
├── frontmatter.py     # + update_text: modifica chirurgica di singoli campi
├── gitops.py          # commit di file specifici, push raggruppato (orologio iniettabile)
├── board_api.py       # logica pura: snapshot, create, update (nessun HTTP)
├── board_server.py    # http.server su 127.0.0.1: token, Host, routing, lock, ciclo di vita
└── cli.py             # + board, + tasks add, + tasks update
toolkit/board/index.html   # UI: un solo file, JS vanilla, nessuna libreria
skills/board/SKILL.md      # /sb:board [stop|status]
```

**Confini:**
- `board_api` non conosce HTTP e si testa direttamente;
- `board_server` è un adattatore sottile;
- la UI parla solo JSON e non conosce il formato dei file.

### 2.1 Path della wiki (tutti i comandi)

Ordine di risoluzione:
1. `--wiki <path>`;
2. la variabile d'ambiente `SB_WIKI`;
3. la cartella corrente o una sua cartella madre.

Non esiste un file di configurazione dedicato.

### 2.2 Avvio e ciclo di vita

- `sb board [--port 8765] [--no-open]`:
  1. trova la wiki;
  2. sceglie la porta: quella indicata, altrimenti le 10 successive; se sono tutte occupate esce con codice 2;
  3. genera un token casuale;
  4. scrive `.sb/board.json` con `{pid, port, url, started}`;
  5. stampa su stdout lo stesso JSON;
  6. apre il browser, salvo `--no-open`.
- Se `.sb/board.json` punta a un processo vivo, `sb board` restituisce quell'URL senza avviare un secondo server. Se il processo è morto, il file viene ignorato e sovrascritto.
- **Arresto** con SIGTERM o SIGINT: push finale, rimozione di `.sb/board.json`, uscita con codice 0.

## 3. UI

Riferimento visivo: la tavola, look "carta e terracotta".
- **Colori:** fondo `#F2ECE3`, card `#FBF8F3`, un solo accento terracotta `#A2461E`.
- **Colonne:** colorate tono su tono, nella famiglia sabbia, ocra, argilla, salvia, pietra.
- **Font:** Instrument Sans 12px più IBM Plex Mono per date e contatori, con fallback di sistema. I font si caricano da Google Fonts; se non sono disponibili si usano quelli di sistema.

### 3.1 Struttura

- **Header**, da sinistra a destra:
  - nome del prodotto: il nome della wiki, cioè quello della cartella;
  - selettore di vista;
  - ricerca;
  - filtri Progetto, Persona, Priorità;
  - interruttore "Mostra chiusi";
  - indicatore di sync;
  - pulsante **Nuovo**.
- **Riga di sintesi:** aperti, scaduti, delegati.
- **Colonne** con le card. In fondo a ogni colonna "Aggiungi task", e un "+" nell'intestazione.
- **Pannello di dettaglio sospeso:** si apre sopra la board, con margine dall'header, angoli arrotondati e ombra. **Non sposta le colonne.**

### 3.2 Viste

| Vista | Colonne | Trascinare o creare in colonna imposta |
|---|---|---|
| **Stato** (`1`) | i valori di `status` dello schema tranne `dropped`; Done mostra solo i task chiusi con `updated` (o `created`) negli ultimi 7 giorni | `status` |
| **Priorità** (`2`) | i valori di `priority` dello schema, più "Senza priorità" | `priority` (Senza priorità = rimuove il campo) |
| **Persone** (`3`) | "Io", più una colonna per ogni owner con task aperti | `owner` ("Io" = rimuove l'owner) |

- I task chiusi sono nascosti nelle viste Priorità e Persone, salvo "Mostra chiusi".
- Ordine dentro una colonna: prima per scadenza (quelli senza data in fondo), poi per titolo. Non si riordina a mano.
- Le colonne di Stato e Priorità seguono gli enum dello schema. Le etichette italiane sono note per i valori del preset; per gli altri valori si usa il valore stesso.

### 3.3 Card

- **Contenuto:** titolo, chip della scadenza (scaduto in terracotta, entro `due_soon_days` in ambra), chip della priorità, fino a 2 chip `related`, iniziali dell'owner se delegato.
- **Azioni rapide al passaggio del mouse o al focus:**
  - ✓ chiudi o riapri;
  - scadenza: +1 giorno, venerdì, +1 settimana, scegli una data, nessuna;
  - priorità: cicla tra i valori dello schema e nessuna.
- **Drag & drop** HTML5 nativo tra colonne; la colonna di destinazione si evidenzia durante il trascinamento.

### 3.4 Pannello di dettaglio

- **Campi modificabili:** titolo (passa da `retitle`), stato, owner (persone + "Io"), scadenza, priorità, collegati (selezione multipla tra persone e progetti).
- **Corpo:** in **sola lettura**, più un campo "Aggiungi nota" che accoda `- AAAA-MM-GG: <testo>`.
- **"Comando per Claude":** copia `/sb:tasks update "<titolo>" ` negli appunti, per le modifiche che richiedono l'LLM.

### 3.5 Creazione

- **Rapida in colonna:** solo il titolo; il campo della vista viene impostato dalla colonna. Invio conferma, Esc annulla.
- **Completa:** il pulsante Nuovo apre un form con titolo, stato, owner, scadenza, priorità, collegati e nota.

### 3.6 Tastiera e aggiornamento

- **Tastiera:**
  - `j`/`k` card precedente e successiva, `Invio` apre il dettaglio, `x` chiudi o riapri;
  - `n` nuovo, `/` cerca, `1`/`2`/`3` cambia vista, `Esc` chiude pannello o form.
  - I tasti sono gestiti sulla pagina e ignorati quando il focus è in un campo di testo.
- **Aggiornamento:** polling di `GET /api/version` ogni 5 s. Se la versione cambia, la board ricarica lo snapshot mantenendo vista, filtri, ricerca e card selezionata.
- **Modifiche ottimistiche:** la UI aggiorna subito e torna indietro se il server rifiuta, con un messaggio in basso.

## 4. API

Il server ascolta solo su `127.0.0.1`. Per tutti gli `/api/*`:
- serve l'header `X-SB-Token` uguale al token di avvio;
- `Host` deve essere `127.0.0.1:<porta>` o `localhost:<porta>`;
- altrimenti risponde `403`.

La pagina `/` riceve il token nella query `?t=`.

| Metodo | Percorso | Risposta |
|---|---|---|
| GET | `/` | `toolkit/board/index.html` |
| GET | `/api/snapshot` | `{wiki, today, thresholds, enums, tasks, people, projects, sync}` |
| GET | `/api/version` | `{version}` |
| POST | `/api/tasks` | `201 {task}`, oppure `409`/`422` |
| PATCH | `/api/tasks` | `200 {task}`, oppure `409`/`422` |

Dettaglio dei campi dello snapshot:
- **`wiki`**: `{name, root}`.
- **`enums`**: `{status: [...], priority: [...], closed: [...]}`, presi dallo schema del tipo `task`.
- **`tasks`**: il contratto di `tasks list` (spec Core §5) più `body` ed `etag` (sha1 del file).
- **`people`**: `[{title, path}]` delle pagine `person` con status non chiuso.
- **`projects`**: `[{title, path}]` delle pagine `project`.
- **`sync`**: `{git: bool, head, pending_push: bool, last_push, last_error}`.

**`version`** è l'hash di commit HEAD più, per ogni file `.md` in `operations/tasks/`, nome e mtime.

**Creazione** (`POST`): body `{title, status?, owner?, due?, priority?, related?, note?}`.

**Modifica** (`PATCH`): body `{path, etag, set?: {campo: valore | null}, note?}`. I campi ammessi in `set` sono `title`, `status`, `owner`, `due`, `priority`, `related`.

## 5. Regole di scrittura

1. **Concorrenza ottimistica.** Se l'`etag` non corrisponde al file su disco, risponde `409 {error, task}` con il task attuale.
2. **Valori espliciti, nessuna inferenza.**
   - `owner` è un titolo di pagina `person`, `related` una lista di titoli di pagine esistenti; il server scrive `"[[Titolo]]"`.
   - `due` è una data ISO.
   - `status` e `priority` devono essere valori degli enum.
   - `null` rimuove il campo.
   - Un valore non valido → `422` prima di scrivere.
3. **Modifica chirurgica del frontmatter** con `frontmatter.update_text(text, changes)`:
   - sostituisce la riga, o il blocco, di ogni campo toccato;
   - aggiunge in fondo i campi nuovi;
   - toglie i campi messi a `null`;
   - lascia intatti commenti, ordine, stile e righe degli altri campi.

   Ogni modifica imposta anche `updated` a oggi.
4. **Cambio di titolo** con l'operazione `retitle` di `migrate`, che rinomina il file e riscrive i link.
5. **Nota:** accoda `- AAAA-MM-GG: <testo>` al corpo, su una riga nuova.
6. **Creazione:**
   - il file è `operations/tasks/<titolo>.md` e il titolo deve rispettare le regole dei nomi;
   - se esiste già una pagina con quel titolo, risponde `409 {error, path}`;
   - frontmatter nell'ordine `type, title, status, owner, due, priority, related, created`, con solo i campi valorizzati; corpo = la nota, se presente.
7. **Validazione:** `validate` sulla sola pagina toccata. Se ci sono errori:
   - una modifica ripristina i byte originali;
   - una creazione cancella il file;
   - risponde `422 {error, issues}`.
8. **Chiusura** a validazione riuscita:
   1. `index`;
   2. `log` con `--op board`;
   3. `git commit` dei **soli file toccati** (il task, ed eventuali pagine riscritte da `retitle`) più `index.md` e `log.md`, con messaggio `sb(board): <titolo> → <modifica>`.

   La board non usa mai `git add -A`.
9. **Commit fallito:** la modifica resta, la risposta porta `committed: false` e i file vengono messi in coda. Il commit successivo li include.
10. **Push raggruppato:** al massimo uno ogni 60 secondi in background, più uno all'arresto. Un push fallito viene ritentato al giro successivo; l'errore compare in `sync.last_error`.
11. **Concorrenza nel processo:** un lock serializza creazioni e modifiche.

## 6. Nuovi comandi del toolkit

- `sb board [--port N] [--no-open]` (§2.2).
- `sb tasks add --title T [--status S] [--owner P] [--due D] [--priority X] [--related R]… [--note N]`
- `sb tasks update <path> [--set campo=valore]… [--unset campo]… [--note N] [--etag E]`

Gli ultimi due condividono la logica di `board_api` e seguono le stesse regole di §5, commit compreso. Le skill `/sb:tasks` li usano al posto della scrittura manuale del frontmatter.

Skill **`/sb:board [stop | status]`**:
- **avvio:** lancia `sb board` in background, apre l'URL e la prima volta propone l'alias `sb`;
- **`stop`:** invia SIGTERM al `pid` di `.sb/board.json`;
- **`status`:** mostra porta, URL, stato del push e ultimo errore, leggendo `/api/snapshot`.

## 7. Errori

| Situazione | Comportamento |
|---|---|
| Porta occupata | Prova le 10 successive, poi esce con codice 2 |
| Board già avviata | Restituisce l'URL esistente |
| Token o `Host` non validi | `403` |
| Etag non aggiornato | `409` con il task attuale |
| Validazione fallita | Ripristino e `422` con le issue |
| Titolo duplicato | `409` con il percorso esistente |
| La wiki non è un repo git | Scrive e valida; `sync.git: false`, niente commit né push |
| Commit fallito | `committed: false`, i file vanno in coda |
| Push fallito | Nuovo tentativo al giro successivo, `sync.last_error` |
| Errore inatteso | `500 {error}`, dettaglio su stderr, il server resta attivo |

## 8. Test

- **`frontmatter.update_text`:** sostituzione, aggiunta e rimozione di un campo; blocchi (liste e mappe) sostituiti per intero; commenti e altri campi identici byte per byte; file senza frontmatter.
- **`board_api`**, su wiki temporanee che sono repo git:
  - snapshot (contratto, enum, persone uscite escluse, etag);
  - creazione (valida, titolo vietato, duplicato, owner inesistente);
  - modifica (ogni campo, `null`, etag non aggiornato, valore fuori enum, `retitle` con link riscritti, nota);
  - validazione fallita con ripristino byte per byte;
  - commit dei soli file toccati, con un file estraneo modificato che non deve finire nel commit.
- **`gitops`:** commit selettivo; push raggruppato con orologio iniettabile verso un remote nudo locale; push fallito che viene ritentato.
- **`board_server`:** server vero su porta effimera, in un thread:
  - `403` senza token o con `Host` sbagliato;
  - routing e codici di risposta;
  - due `PATCH` concorrenti con lo stesso etag → una `200` e una `409`;
  - `.sb/board.json` scritto all'avvio e rimosso all'arresto.
- **CLI:** `tasks add`, `tasks update`; `SB_WIKI`; `board` con `--no-open` su porta effimera.
- **UI:** scenari manuali in `tests/scenarios/` e smoke test `curl` degli endpoint.

## 9. Fuori scope

- Telefono e accesso remoto.
- Riordino manuale delle card dentro una colonna.
- Modifica libera del corpo dei task.
- Più utenti in contemporanea.
- Viste diverse dai task (rischi, decisioni).
