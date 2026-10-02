---
name: team
layer: knowledge
folder: knowledge/teams
fields:
  lead: {kind: link, to: person}
  parent: {kind: link, to: team}
  status: {kind: enum, values: [active, dissolved], closed: [dissolved]}
---
# Team

Un team o un'unità organizzativa: squadre di prodotto, piattaforma, chapter, gruppi trasversali.

**Crea** una pagina per ogni team che riporta a te, che dipende da te o con cui collabori stabilmente.

**Non creare** pagine per gruppi temporanei di una sola riunione: quelli sono `meeting`.

**Struttura del corpo**:
- `## Missione e perimetro`: di cosa si occupa, quali sistemi e progetti possiede (con link).
- `## Persone`: membri e ruoli, con link alle pagine `person`.
- `## Modo di lavorare`: rituali, on-call, metriche seguite.
- `## Salute`: carico, morale, rischi ricorrenti, con link a `risk` e `one-on-one`.
- `## Note`: valutazioni dell'utente.
