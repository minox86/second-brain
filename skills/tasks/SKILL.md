---
name: tasks
description: Mostra e gestisce i task della wiki Second Brain (tuoi, delegati, scaduti, di oggi o della settimana) e permette di crearli, chiuderli, abbandonarli o aggiornarli. Usa per "cosa devo fare oggi?", "cosa aspetto dagli altri?", "chiudi il task…", "sposta la scadenza di…", "aggiungi un task…".
argument-hint: "[mine|delegated|overdue|today|week|blocked|all] [--project X] [--person Y] [--priority P] | add <testo> | done <task> | drop <task> | update <task> <modifica>"
---

# /sb:tasks: vedere e gestire i task

Argomenti: `$ARGUMENTS`

Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.

## Viste (solo lettura)

Si applicano quando il primo argomento è una vista, un filtro, oppure manca (default `mine`). In linguaggio naturale: "oggi" → `today`, "questa settimana" → `week`, "cosa aspetto dagli altri" → `delegated`.

1. `SB tasks list --view <vista> [--project …] [--person …] [--priority …]`
2. Mostra una tabella compatta nell'ordine restituito: `#` · titolo · stato · owner (solo se delegato) · scadenza (⚠️ se `overdue`) · priorità. Oltre le 20 righe, mostra le prime 20 e il totale.
3. Riga finale: aperti · scaduti · delegati. Se utile, suggerisci un'altra vista.

Nessun commit.

## Azioni

Le azioni usano i comandi deterministici del toolkit, gli stessi della board. Questi comandi validano, aggiornano l'indice, scrivono il log e fanno commit e push da soli: **non** eseguire il flusso di chiusura delle convenzioni dopo di loro.

- **`add <testo>`**:
  1. inferisci i campi come indicato nella prosa del tipo `task` e nella skill put, passo 5;
  2. esegui `SB tasks add --title "<titolo>" [--owner "<persona>"] [--due AAAA-MM-GG] [--priority <valore>] [--status <valore>] [--related "<titolo>"]… [--note "<contesto>"]`;
  3. se il testo ha un contesto da conservare come fonte, catturalo prima in `raw/` (`kind: dictation`) e citalo nella nota.
- **`done <task>` / `drop <task>`**:
  1. risolvi con `SB resolve "<task>" --type task`; se è ambiguo, mostra i candidati e chiedi;
  2. esegui `SB tasks update "<path>" --set status=done` (oppure `status=dropped`), aggiungendo `--note "chiuso"` o `--note "abbandonato: <motivo>"`.
- **`update <task> <modifica>`**:
  1. risolvi come sopra;
  2. traduci la richiesta in `--set campo=valore` (campi: `title`, `status`, `owner`, `due`, `priority`, `related=A,B`) e `--unset campo`, più `--note "<cosa è cambiato>"`.

  Un cambio di `title` rinomina il file e riscrive i link in automatico.

Se il comando esce con codice 2, mostra il campo `error` del JSON. Per un duplicato, il campo `path` indica il task già esistente. Se la risposta ha `committed: false`, segnala che il commit è in sospeso. Conferma in una riga cosa è cambiato.
