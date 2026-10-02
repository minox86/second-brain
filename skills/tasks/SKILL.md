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

- **`add <testo>`**: crea un task con le regole della prosa del tipo `task` e della skill put (passo 5).
  - Se il testo contiene contesto oltre al titolo, catturalo in `raw/` (`kind: dictation`) e citalo.
  - Altrimenti lascia `sources` vuoto.
- **`done <task>` / `drop <task>`**:
  1. Risolvi con `SB resolve "<task>" --type task`; se è ambiguo, mostra i candidati e chiedi.
  2. Imposta `status: done` o `dropped` e aggiorna `updated`.
  3. Accoda al corpo `- AAAA-MM-GG: chiuso`, oppure `- AAAA-MM-GG: abbandonato: <motivo>` se l'utente lo indica.
- **`update <task> <modifica>`**:
  1. Risolvi come sopra.
  2. Applica la modifica descritta in linguaggio naturale: scadenza, priorità, owner, stato (`blocked` con il motivo nel corpo), titolo. Per cambiare titolo usa un'operazione `retitle` con `SB migrate`, così i link restano validi.
  3. Accoda `- AAAA-MM-GG: <cosa è cambiato>`.

Dopo ogni azione esegui il flusso standard con `--op tasks` e conferma in una riga cosa è cambiato.
