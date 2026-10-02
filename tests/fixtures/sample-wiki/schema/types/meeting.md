---
name: meeting
layer: operations
folder: operations/meetings
fields:
  date: {kind: date}
  series: {kind: string}
  attendees: {kind: list, of: link, to: person}
  project: {kind: link, to: project}
required: [date]
---
# Meeting

Una riunione con più partecipanti: staff meeting, review, planning, incontri con stakeholder, incident review.

**Crea** una pagina per ogni riunione con contenuto rilevante (decisioni, task, informazioni nuove). Titolo: `AAAA-MM-GG <nome della riunione>`. `series` raggruppa le ricorrenze (es. `Weekly Platform`).

**Non creare** pagine per riunioni senza contenuto da ricordare.

**Struttura del corpo**:
- `## Contesto`: perché si è tenuta.
- `## Punti`: cosa è emerso, con link.
- `## Decisioni`: link alle pagine `decision` create.
- `## Azioni`: link ai task creati.
- `## Note`: valutazioni dell'utente.
