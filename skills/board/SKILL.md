---
name: board
description: Apre, ferma o controlla la board visuale dei task della wiki Second Brain, una pagina locale nel browser per vedere, trascinare, chiudere e creare task. Usa per "apri la board", "fammi vedere i task in kanban", "chiudi la board", "la board è accesa?".
argument-hint: "[stop | status | sempre | non sempre]"
---

# /sb:board: la board dei task

Argomenti: `$ARGUMENTS`

Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill. La board è un server locale (`127.0.0.1`) avviato dal toolkit. Le modifiche fatte nel browser passano dal toolkit e finiscono in commit `sb(board): …`.

## Senza argomenti: avvio

1. Controlla `.sb/board.json` nella radice della wiki. Se esiste, la board potrebbe essere già attiva: il comando del passo 2 lo verifica da solo e, se è attiva, restituisce l'URL esistente.
2. Avvia il server **in background** (Bash con `run_in_background: true`):

        SB board

   Poi leggi la prima riga dell'output: è un JSON con `url`, `port` e `pid`, oppure `already_running: true` con l'URL già attivo.
3. Il comando apre il browser da solo. In più, mostra all'utente l'URL completo (contiene il token). L'URL resta lo stesso a ogni avvio (token e porta stanno in `.sb/board-key.json`), quindi si può salvare nei preferiti. Se il JSON ha `warning`, la porta salvata era occupata: riporta il messaggio, perché il preferito va aggiornato.
4. **Prima volta in questa wiki:** proponi una volta l'alias per usare la board dal terminale senza Claude Code, da aggiungere a `~/.zshrc`:

        alias sb='python3 "<radice del plugin>/toolkit/sb.py"'

   Aggiungi anche `export SB_WIKI="<radice della wiki>"`, se l'utente vuole lanciare `sb board` da qualunque cartella. Non modificare file di configurazione senza il suo ok.

## `sempre`: board sempre accesa (solo macOS)

Quando l'utente vuole la board sempre disponibile, per esempio dai preferiti del browser:

1. Esegui `SB board --install`. Il comando installa un LaunchAgent in `~/Library/LaunchAgents/` che avvia la board al login e la riavvia se cade; se c'era una board avviata a mano, la ferma e cede il posto all'agente.
2. Dal JSON mostra `url` (da mettere nei preferiti) e `log` (`.sb/board.log`, dove guardare se non risponde).
3. L'agente usa il toolkit dal percorso attuale del plugin: dopo un aggiornamento del plugin che lo sposta, ripeti `SB board --install`.

## `non sempre`

Esegui `SB board --uninstall` e conferma con una riga. Il token resta salvato: un nuovo avvio riusa lo stesso URL.

## `stop`

1. Leggi `pid`, `port` e `url` da `.sb/board.json`. Se il file manca, la board non è attiva: dillo.
2. Verifica che quel processo sia davvero la board: `curl -s -o /dev/null -w "%{http_code}" -H "X-SB-Token: <token>" "http://127.0.0.1:<port>/api/version"`, con il token preso dall'URL, deve rispondere `200`. Se non risponde, il file è rimasto da una sessione chiusa male e il `pid` può appartenere a un altro processo: **non** inviare segnali, cancella `.sb/board.json` e dillo.
3. `kill -TERM <pid>` (SIGTERM). Il server fa il push finale e rimuove `.sb/board.json`.
4. Conferma con una riga. Se `.sb/board.json` esiste ancora dopo qualche secondo, dillo all'utente invece di forzare con `kill -9`.
5. Se è installata la board sempre accesa, lo stop vale fino al prossimo login: per spegnerla del tutto serve `non sempre`.

## `status`

1. Leggi `.sb/board.json`. Se manca: "board non attiva".
2. Chiedi lo snapshot usando il token preso dall'URL:

        curl -s -H "X-SB-Token: <token>" "http://127.0.0.1:<port>/api/snapshot"

   Dal JSON leggi `sync`.
3. Mostra in 2–4 righe:
   - porta e URL;
   - `head`;
   - push in coda (`pending_push`) e ultimo push (`last_push`);
   - eventuali `last_error`, `commit_error` e `uncommitted`.

## Note

- La board scrive solo i campi espliciti (stato, owner, scadenza, priorità, collegati, titolo, note). Le modifiche che richiedono l'LLM si fanno da Claude Code: il pannello ha "Comando per Claude", che copia `/sb:tasks update "<titolo>" `.
- Le modifiche fatte da Claude Code o da Obsidian mentre la board è aperta compaiono nella board entro 5 secondi.
