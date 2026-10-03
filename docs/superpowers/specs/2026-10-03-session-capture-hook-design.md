# Hook di cattura delle sessioni: design

- **Data:** 2026-10-03
- **Stato:** approvato in brainstorming, in revisione
- **Ambito:** primo hook del plugin `sb`
- **Dipende da:** `docs/superpowers/specs/2026-10-02-second-brain-core-design.md` (skill `put`, flusso di chiusura)

## 1. Obiettivo

Oggi una conversazione dentro la wiki alimenta la wiki solo se Claude decide di attivare `put` partendo dalla sua descrizione. Le informazioni dette di passaggio, mentre si fa altro (`ask`, `prep`, `tasks`…), vanno perse.

L'hook fa in modo che le parti rilevanti di ogni sessione **vengano valutate** e, se servono, **salvate in automatico** con `put`.

Decisioni prese in brainstorming:

- **Ambito:** solo le sessioni con `cwd` dentro una wiki Second Brain. Le sessioni in altri repo vengono ignorate, anche se `SB_WIKI` è impostata.
- **Azione:** salvataggio automatico. Claude lancia `put` senza chiedere, commit e push compresi. Restano valide le regole di conferma di `put` (entità ambigue, tipo incerto, `--plan`).
- **Cadenza:** a fine turno (hook `Stop`), con un filtro deterministico che salta i turni senza contenuto.

Il filtro decide solo **se** chiedere la valutazione. Cosa sia rilevante lo giudica Claude.

## 2. Architettura

```
hooks/hooks.json            # Stop → python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/sb.py" hook stop
toolkit/sb_core/capture.py  # logica pura: transcript + cursore → decisione
toolkit/sb_core/cli.py      # + sottocomando `hook stop` (stdin JSON → stato → output)
<wiki>/.sb/capture.json     # stato: cursore per sessione (già ignorato da git)
```

### 2.1 `hooks/hooks.json`

Un solo hook `Stop` di tipo `command`, senza matcher:

    python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/sb.py" hook stop

Timeout breve (10 s): l'hook legge solo file locali.

### 2.2 `capture.py`

Funzioni pure, senza I/O sul transcript reale né sullo stato:

- `user_texts(entries)`: i messaggi reali dell'utente, cioè voci con `type: "user"`, senza `isMeta` e senza `isSidechain`, con `content` stringa o blocchi `text` (mai `tool_result`). Esclude gli output dei comandi locali (`<local-command-stdout>`, `<local-command-caveat>`).
- `put_ran(entries)`: vero se fra le voci c'è un `tool_use` `Skill` con `skill` uguale a `sb:put`, oppure un messaggio utente che invoca `/sb:put` (`<command-name>/sb:put</command-name>`).
- `after(entries, cursor)`: le voci successive a quella con `uuid == cursor`. Se il cursore manca o non si trova, tutte le voci.
- `decide(entries, cursor, threshold)` restituisce `(block: bool, new_cursor)`:
  1. `tail = after(entries, cursor)`;
  2. se `put_ran(tail)`: niente blocco, cursore all'ultima voce con `uuid`;
  3. se la lunghezza totale di `user_texts(tail)` è almeno `threshold`: blocco, cursore all'ultima voce con `uuid`;
  4. altrimenti: niente blocco, cursore invariato, così il testo si accumula sui turni successivi.

Soglia predefinita: **200 caratteri** (`DEFAULT_THRESHOLD`).

### 2.3 `sb hook stop`

1. Legge il JSON da stdin: `session_id`, `transcript_path`, `cwd`, `stop_hook_active`.
2. Esce con `0` senza output se:
   - `SB_CAPTURE` vale `0`, `off` o `false`;
   - `stop_hook_active` è vero (è lo stop dopo la valutazione: evita il loop);
   - `find_root(cwd)` non trova una wiki;
   - il transcript non esiste o non si legge.
3. Carica `.sb/capture.json` (`{"sessions": {"<session_id>": {"cursor": "<uuid>", "seen": "<ISO>"}}}`). Uno stato illeggibile riparte vuoto.
4. Chiama `decide`, salva il nuovo cursore e pota le sessioni non viste da più di 30 giorni.
5. Se c'è da bloccare, stampa su stdout il JSON di blocco dell'evento `Stop`, nel formato documentato da Claude Code (da verificare in implementazione: `{"decision": "block", "reason": "…"}`).

Qualsiasi eccezione imprevista porta a `exit 0` senza output: l'hook non deve mai rompere né bloccare la sessione per un suo errore.

### 2.4 Messaggio di blocco

Il messaggio è breve, in italiano, e l'utente lo vede come feedback dell'hook. Non ricopia il transcript, perché Claude ha già la conversazione in contesto. Contenuto:

> Second Brain: valuta i messaggi dell'utente dall'ultima valutazione. Se contengono fatti, decisioni, task, rischi, eventi (1:1, riunioni) od opinioni utili alla wiki e non ancora salvati, lancia /sb:put con quel contenuto senza chiedere conferma, poi riassumi in una riga cosa è entrato. Se non c'è niente di nuovo, rispondi solo «Niente da salvare nella wiki.»

## 3. Casi limite

- **Loop:** dopo il blocco Claude lavora e si ferma di nuovo con `stop_hook_active: true`, e l'hook esce subito. Al turno utente successivo il cursore è già avanzato, quindi il materiale valutato non viene riproposto.
- **`put` lanciato spontaneamente:** il punto 2 di `decide` fa avanzare il cursore senza bloccare, così non si fa una doppia valutazione.
- **Risposte brevi** («sì», «ok», conferme di `put`): restano sotto soglia e si accumulano.
- **Compattazione o resume:** se il cursore non si trova più nel transcript, si rivaluta tutto. Al peggio Claude riceve una valutazione in più e risponde «niente da salvare».
- **Subagenti:** le voci `isSidechain` sono escluse. L'hook `SubagentStop` non si usa.
- **Comandi `sb` di sola lettura** (`ask`, `prep`, `status`…): vengono valutati come qualsiasi altro turno. È proprio il caso in cui oggi le informazioni si perdono.

## 4. Test

- `tests/test_capture.py`: unit test di `capture.py` su transcript costruiti in memoria. Coprono soglia, accumulo, `put` via `Skill` e via `/sb:put`, voci meta, sidechain e `tool_result` ignorate, cursore assente o sconosciuto.
- Test CLI di `sb hook stop` con stdin su una wiki fixture: fuori wiki, `stop_hook_active`, `SB_CAPTURE=0`, transcript mancante, blocco con output JSON, persistenza e potatura dello stato, stato corrotto.
- `tests/test_plugin_layout.py`: `hooks/hooks.json` esiste, registra un hook `Stop` e il comando punta a `toolkit/sb.py hook stop`.

## 5. Documentazione

- README: sezione "Cattura automatica" (cosa fa, quando scatta, come spegnerla con `SB_CAPTURE=0`).
- `templates/wiki/CLAUDE.md`: una riga nelle regole che spiega la valutazione a fine turno.

## 6. Fuori scope

- Cattura dalle sessioni fuori dalla wiki.
- Elaborazione in background a fine sessione (`SessionEnd` + `claude -p`).
- Soglia o messaggio configurabili da `schema/wiki.md`.
