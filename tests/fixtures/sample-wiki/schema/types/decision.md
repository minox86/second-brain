---
name: decision
layer: operations
folder: operations/decisions
fields:
  date: {kind: date}
  status: {kind: enum, values: [proposed, accepted, rejected, superseded], closed: [accepted, rejected, superseded]}
  decided_by: {kind: list, of: link, to: person}
  project: {kind: link, to: project}
  supersedes: {kind: link, to: decision}
---
# Decision

Una decisione rilevante, nello stile di un ADR leggero: tecnica, organizzativa, di priorità.

**Crea** una pagina quando viene presa o proposta una decisione che qualcuno vorrà ritrovare ("perché abbiamo scelto X?"). Titolo: `AAAA-MM-GG <decisione in breve>`.

**Non creare** pagine per scelte operative minori senza impatto oltre la settimana.

**Struttura del corpo**:
- `## Contesto`: il problema e i vincoli.
- `## Decisione`: cosa si è deciso.
- `## Alternative considerate`: con il motivo per cui sono state scartate.
- `## Conseguenze`: cosa cambia; aggiorna anche le pagine knowledge interessate.
- `## Note`: valutazioni dell'utente.

Quando una decisione ne sostituisce un'altra: `supersedes` sulla nuova e `status: superseded` sulla vecchia.
