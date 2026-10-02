---
name: risk
layer: operations
folder: operations/risks
fields:
  status: {kind: enum, values: [open, mitigating, closed, accepted], closed: [closed, accepted]}
  likelihood: {kind: enum, values: [low, medium, high]}
  impact: {kind: enum, values: [low, medium, high]}
  owner: {kind: link, to: person}
  project: {kind: link, to: project}
  review: {kind: date}
---
# Risk

Un rischio da seguire: delivery, persone (retention, burnout, single point of failure), tecnico, di fornitore, di budget.

**Crea** una pagina quando un rischio viene nominato esplicitamente o emerge con chiarezza da più segnali.

**Non creare** pagine per preoccupazioni generiche senza un oggetto preciso.

**Struttura del corpo**:
- `## Descrizione`: cosa può succedere e perché.
- `## Segnali`: evidenze datate con fonte.
- `## Mitigazioni`: azioni in corso, con link ai task.
- `## Note`: valutazioni dell'utente.

`likelihood` e `impact` vanno valorizzati solo se dichiarati o deducibili con chiarezza. `review` è la prossima data di revisione.
