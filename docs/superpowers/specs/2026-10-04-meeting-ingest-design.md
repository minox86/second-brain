# Skill `meeting`: ingestione delle riunioni da Microsoft 365

- **Data:** 2026-10-04
- **Stato:** approvato in brainstorming, in revisione
- **Ambito:** nuova skill `/sb:meeting` e due sottocomandi del toolkit (`meeting capture`, `meeting seen`)
- **Dipende da:** `docs/superpowers/specs/2026-10-02-second-brain-core-design.md` (skill `put`, convenzioni, flusso di chiusura)

## 1. Obiettivo

Far entrare nella wiki le riunioni Teams senza copiare nulla a mano. La skill trova la riunione nel calendario, scarica tutto ciò che il connettore Microsoft 365 rende disponibile (evento, trascrizione, chat) e lo passa alla pipeline di `put`.

Tre modi d'uso:

1. **per riferimento**: nome della riunione, link Teams o testo libero ("la review roadmap di venerdì");
2. **lista del giorno**: elenca le riunioni di oggi (o di una data) e chiede quali ingerire;
3. **"la riunione appena finita"**.

Decisioni prese in brainstorming:

- **Senza trascrizione:** la skill lo dice e chiede un breve dettato all'utente; lo unisce a evento e chat e ingerisce. Se l'utente risponde "salta", la riunione non entra.
- **Grezzo:** la trascrizione completa e intatta va in `raw/`, versionata e pushata come ogni altro grezzo.
- **Valutazioni:** con la trascrizione presente la skill non chiede valutazioni. `## Note` resta vuota.
- **Architettura:** skill per la parte conversazionale e MCP; toolkit per la parte meccanica e testabile; analisi e scrittura delegate ai passi 3–7 di `put`.

## 2. Cosa espone il connettore (verificato il 2026-10-04)

| Risorsa | Come si ottiene | Note |
|---|---|---|
| Evento | `outlook_calendar_search` → `read_resource(calendar:///events/<id>)` | Oggetto, orari, organizzatore, partecipanti con nome ed email, corpo HTML, `onlineMeeting.joinUrl`, `meetingTranscriptUrl`, `recurrence` |
| Trascrizione | `read_resource(<meetingTranscriptUrl>)` | JSON `{meeting, transcripts: [{id, createdDateTime, endDateTime, content}]}`; `content` è WEBVTT con `<v Nome>` e timestamp. Può essere vuota (non trascritta, o visibile solo all'organizzatore). Per una serie si aggiunge `?start=<iso>&end=<iso>` |
| Chat della riunione | `read_resource(teams:///chats/<thread>/messages)` | `<thread>` = `19:meeting_…@thread.v2`, ricavato dal `joinUrl`. Restituisce messaggi (`messageType: message`, con `bodyPreview` troncato) ed eventi di sistema (`callStarted`, `callEnded` con `callParticipants`, `callRecording` con `callRecordingUrl`, `callTranscript`). Il testo completo di un messaggio si legge con `read_resource` sul suo `uri` |
| Recap Copilot | non disponibile | Lo scope `OnlineMeetingAiInsight.Read.All` è concesso ma il connettore non ha un tipo di URI per leggerlo; non è pubblicato in chat |

Vincoli osservati:

- **La ricerca solo testuale restituisce ID non leggibili** (formato con `/`, `read_resource` risponde 400). La ricerca con `afterDateTime`/`beforeDateTime` restituisce ID leggibili. La skill cerca **sempre** dentro una finestra di date.
- **Le trascrizioni lunghe non arrivano inline**: oltre la soglia di output il risultato MCP viene salvato su file e Claude riceve il percorso. Una call di 1h26 produce circa 82K caratteri.

## 3. Architettura

```
skills/meeting/SKILL.md      # risoluzione, lista, recupero MCP, orchestrazione
toolkit/sb_core/meeting.py   # logica pura: rendering del raw, slug, chat, presenze, seen
toolkit/sb_core/cli.py       # + `meeting capture`, `meeting seen`
tests/test_meeting.py        # unit e CLI
tests/fixtures/meeting/      # evento, trascrizione corta, chat (anonimizzati)
```

Il toolkit non chiama MCP. La skill salva le risposte MCP in file JSON e passa i percorsi al toolkit, che scrive il raw senza far passare la trascrizione dall'output del modello.

## 4. Skill `/sb:meeting`

`argument-hint: "[oggi | ieri | AAAA-MM-GG | ultima | <link Teams> | <testo>]"`

La `description` include i trigger in linguaggio naturale: "aggiungi la riunione appena finita", "ingerisci le riunioni di oggi", "salva la riunione X", link `teams.microsoft.com/meet/…` o `…/l/meetup-join/…`.

### 4.0 Prima di iniziare

1. Legge `BASE/../../references/conventions.md` e verifica la wiki con `SB version`.
2. Verifica che i tool Microsoft 365 siano disponibili. In caso contrario lo dice e si ferma.

### 4.1 Risoluzione

| Input | Risoluzione |
|---|---|
| nessuno, `oggi` | Modalità lista su oggi |
| `ieri`, `AAAA-MM-GG` | Modalità lista su quel giorno |
| `ultima`, "appena finita" | Calendario da −12 h ad adesso, `order: newest`. Primo evento non scartato (§4.2) con `end` ≤ adesso + 15 min. Mostra una riga di conferma (oggetto, orario, numero di persone) prima di procedere |
| link `teams.microsoft.com/meet/<n>` | Ricerca di `<n>` con finestra ±60 giorni da oggi |
| link `…/l/meetup-join/19%3ameeting_<x>…` | Ricerca del token `<x>` con finestra ±60 giorni; se non trova, confronto di `onlineMeeting.joinUrl` sugli eventi letti |
| testo libero | Ricerca testuale nella finestra della data citata (convertita in ISO), altrimenti negli ultimi 14 giorni. Un risultato: procede. Più risultati: domanda a scelta multipla. Nessuno: lo dice e chiede un riferimento più preciso |

La ricerca usa sempre `afterDateTime` e `beforeDateTime` (§2). Gli orari si mostrano nel fuso dell'utente, convertiti dal `timeZone` dell'evento.

### 4.2 Modalità lista

1. Recupera tutti gli eventi del giorno, paginando con `offset`.
2. **Scarta**: `isCancelled`; `showAs` `oof` o `free`; `isAllDay`; eventi senza altri partecipanti oltre all'utente; eventi rifiutati dall'utente.
3. Esegue `SB meeting seen <id>…` sugli ID rimasti.
4. Mostra una domanda a scelta multipla (`multiSelect`) con una riga per riunione: orario, oggetto, numero di persone. Le riunioni già ingerite e quelle non ancora finite compaiono nel testo della domanda ma non sono selezionabili.
5. Nessuna riunione selezionabile: lo dice e termina.

### 4.3 Recupero (per ogni riunione scelta)

1. `read_resource` dell'evento; salva il JSON in `.sb/tmp/meeting-<n>-event.json`.
2. Trascrizione da `meetingTranscriptUrl`, con `?start=&end=` dell'occorrenza se `recurrence` non è nulla. Se il risultato è stato salvato su file, usa quel percorso; se è inline e non vuoto, lo salva in `.sb/tmp/meeting-<n>-transcript.json`.
3. Chat: ricava il thread dal `joinUrl` (decodifica di `19%3ameeting_…%40thread.v2`), legge `teams:///chats/<thread>/messages`, legge il testo completo di ogni `messageType: message` e salva in `.sb/tmp/meeting-<n>-chat.json` la lista dei messaggi con i corpi completi.
4. **Senza trascrizione**: lo dice e chiede: "Raccontami in due righe com'è andata (o 'salta')". Il dettato va in `.sb/tmp/meeting-<n>-dictation.txt`. "salta" esclude la riunione.
5. Errori: evento illeggibile, la riunione si salta e finisce nel riepilogo; chat illeggibile, si procede senza chat e `capture` lo annota nel raw.

### 4.4 Cattura

    SB meeting capture --event <file> [--transcript <file>] [--chat <file>] [--dictation <file>]

Stampa `{"ok": true, "path": "raw/…", "kind": "…"}`. Poi la skill cancella i file in `.sb/tmp/` di quella riunione.

### 4.5 Analisi e scrittura

Esegue i passi 3–7 di `skills/put/SKILL.md` sul raw catturato, con queste regole aggiuntive:

- **Tipo**: `one-on-one` se i presenti effettivi (oppure, se mancano, gli invitati) sono esattamente l'utente più una persona; altrimenti `meeting`.
- **Titolo**: `AAAA-MM-GG <oggetto ripulito>`. Il `one-on-one` segue la sua prosa: `AAAA-MM-GG 1on1 <Nome Cognome>`.
- **`series`**: solo se l'evento è ricorrente; oggetto senza parti variabili.
- **Persone**: `SB resolve "<Nome Cognome>"` per ogni partecipante, con le regole di ambiguità. In `attendees` vanno solo le persone con una pagina esistente o che la prosa di `person` dice di creare; le altre restano testo semplice. L'email non si salva (lo schema `person` non ha il campo); se il bisogno ricorre, segnale di schema.
- **Citazioni**: `^[raw/AAAA/MM/<slug>]`, con il timestamp della trascrizione nel testo quando aiuta ("(00:15:28)").
- **`## Note`**: non si compila.
- **Conferma del piano**: valgono le soglie di `put`.

### 4.6 Chiusura e riepilogo

Un solo flusso di chiusura delle convenzioni per tutte le riunioni del lotto, con `--op meeting`. Messaggio di commit: `sb(meeting): <n> riunioni · <d> decisioni · <t> task`.

Riepilogo: quello di `put` per ogni riunione, più l'elenco delle riunioni saltate con il motivo (non finita, già ingerita, senza trascrizione né dettato, errore del connettore).

## 5. Toolkit

### 5.1 `meeting.py`

Funzioni pure, senza I/O tranne `seen`:

- `agenda_text(html) -> str`: testo del corpo dell'invito, senza il blocco Teams (dalla prima riga di soli `_` in poi) e senza righe vuote ripetute.
- `chat_lines(messages) -> list[str]`: per ogni `messageType == "message"` in ordine cronologico, `HH:MM Nome: testo` (HTML ridotto a testo, link resi come URL). Allegati senza testo: `HH:MM Nome: [allegato]`.
- `attendance(messages) -> dict`: da `callEndedEventMessageDetail` i nomi dei `callParticipants` umani e la durata `callDuration`; da `callRecordingEventMessageDetail` con `callRecordingStatus == "success"` il `callRecordingUrl`. Chiavi assenti se l'informazione manca.
- `transcript_text(payload) -> str | None`: il `content` delle trascrizioni concatenate in ordine di `createdDateTime`, separate da una riga vuota; `None` se non ce ne sono.
- `slug_for(subject) -> str`: minuscolo, ASCII, a trattini, prefissi "Annullata:"/"Canceled:" rimossi, al massimo 60 caratteri.
- `raw_path_for(wiki, event, existing) -> Path`: `raw/AAAA/MM/AAAA-MM-GG-<slug>.md` dalla data di inizio dell'evento; con collisione, suffisso `-2`, `-3`…
- `render_raw(event, transcript, chat_messages, dictation, today) -> str`: il markdown del §5.3.
- `seen(wiki, ids) -> dict[id, path]`: scansione del frontmatter dei `.md` in `raw/` alla ricerca di `origin: "teams:event/<id>"`.

### 5.2 CLI

- `sb meeting capture --event F [--transcript F] [--chat F] [--dictation F]`: legge i file, scrive il raw, stampa `{"ok": true, "path": …, "kind": …}`. Exit 2 se l'evento manca o non è JSON valido, oppure se trascrizione e dettato mancano entrambi. Se esiste già un raw con lo stesso `origin` esce con 1 e `{"ok": false, "error": "already-captured", "path": …}`. Non fa commit.
- `sb meeting seen ID…`: stampa `{"seen": {"<id>": "raw/…"}}`, solo gli ID trovati. Exit 0.

### 5.3 Formato del raw

    ---
    kind: transcript
    captured: 2026-10-04
    origin: "teams:event/<eventId>"
    meeting_date: 2026-09-30
    ---
    # <oggetto>

    ## Evento
    - Orario: 2026-09-30 09:30–10:00 UTC · durata effettiva 1h26
    - Organizzatore: Nome Cognome
    - Invitati: Nome Cognome, …
    - Presenti: Nome Cognome, …
    - Registrazione: <url>

    Agenda:
    <agenda_text>

    ## Chat
    - 10:58 Nome Cognome: <testo>

    ## Trascrizione
    <WEBVTT intatto>

- `kind` vale `transcript` se c'è la trascrizione, altrimenti `dictation`, e al posto di `## Trascrizione` c'è `## Dettato` con il testo dell'utente intatto.
- Le righe e le sezioni senza dati si omettono. Se la chat non era leggibile la sezione dice `_Chat non disponibile._`.
- `origin` identifica la riunione per `seen`; `captured` e `kind` seguono la convenzione di `put`.

## 6. Test

`tests/test_meeting.py`, con fixture in `tests/fixtures/meeting/` derivate dalle risposte reali, anonimizzate e accorciate:

- `agenda_text` toglie il blocco Teams e conserva il testo dell'organizzatore;
- `chat_lines` ignora gli eventi di sistema e rende link e allegati;
- `attendance` estrae presenti, durata e registrazione; regge l'assenza di `callEnded`;
- `transcript_text` con zero, una e due trascrizioni;
- `slug_for` con caratteri accentati, `:`, "Annullata:" e oggetti lunghi;
- `raw_path_for` aggiunge `-2` in collisione;
- `render_raw`: trascrizione **byte per byte** identica nel file; variante con dettato; sezioni vuote omesse;
- `seen` trova e non trova;
- CLI: `capture` scrive il file e risponde JSON; `already-captured`; errori d'uso con exit 2; `seen`.

`tests/test_plugin_layout.py` copre già la forma di ogni skill (niente recinti di codice). Gli scenari di accettazione in `tests/scenarios/README.md` aggiungono: riunione appena finita; lista di oggi con una riunione già ingerita; link Teams; riunione senza trascrizione con dettato.

## 7. File toccati

- Nuovi: `skills/meeting/SKILL.md`, `toolkit/sb_core/meeting.py`, `tests/test_meeting.py`, `tests/fixtures/meeting/*`.
- Modificati: `toolkit/sb_core/cli.py`, `references/conventions.md` (tabella del toolkit), `README.md` (tabella dei comandi), `tests/scenarios/README.md`.

## 8. Fuori ambito

- Recap Copilot: non esposto dal connettore.
- Download della registrazione video: si conserva solo il link.
- Ingestione automatica a fine giornata: si può aggiungere poi con `/schedule`, appoggiandosi a `meeting seen`.
- Riunioni non Teams (Zoom, in presenza): sono gestite solo come eventi senza trascrizione, con il dettato.
