---
name: task
layer: operations
folder: operations/tasks
fields:
  status: {kind: enum, values: [todo, blocked, done, dropped], closed: [done, dropped]}
  owner: {kind: link, to: person}
  due: {kind: date}
  priority: {kind: enum, values: [low, medium, high]}
  related: {kind: list, of: link}
---
# Task

Un'azione concreta da fare: tua, oppure delegata a qualcuno e da tenere d'occhio.

**Crea** un task per ogni impegno esplicito:
- dell'utente: "devo…", "mi prendo…", "entro venerdì mando…";
- di un'altra persona verso l'utente: "Luca mi manda…", "ho chiesto ad Anna di…".

**Non creare** task per intenzioni vaghe ("prima o poi…") o per attività del team che non richiedono di essere seguite dall'utente: quelle stanno nel tool del team.

**Struttura del corpo**: 1–3 righe di contesto con citazione, poi una riga datata per ogni aggiornamento (`- AAAA-MM-GG: …`).

Regole per i campi, tutti opzionali e da inferire solo con ragionevole sicurezza:
- `title`: verbo all'infinito, specifico ("Mandare a Luca la proposta di budget Q4").
- `owner`: solo se l'azione è di un'altra persona. Senza owner il task è dell'utente: non mettere mai l'utente come owner.
- `due`: data assoluta, calcolata rispetto alla data dell'evento d'origine.
- `priority`: solo con segnali espliciti (urgente, bloccante = high; quando puoi = low).
- `status`: `todo` di default; `blocked` solo se dichiarato.
- `related`: evento d'origine ed entità coinvolte.
