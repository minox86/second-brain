---
name: project
layer: knowledge
folder: knowledge/projects
fields:
  status: {kind: enum, values: [proposed, active, paused, done, cancelled], closed: [done, cancelled]}
  owner: {kind: link, to: person}
  team: {kind: link, to: team}
  systems: {kind: list, of: link, to: system}
  start: {kind: date}
  target: {kind: date}
---
# Project

Un'iniziativa con un obiettivo, un responsabile e una durata: progetti di prodotto, migrazioni, programmi trasversali.

**Crea** una pagina quando un'iniziativa ha un nome riconosciuto e compare in più conversazioni o documenti.

**Non creare** pagine per attività di pochi giorni: quelle sono `task`.

**Struttura del corpo**:
- `## Obiettivo`: perché esiste, cosa cambia quando è finito.
- `## Perimetro e architettura`: cosa include ed esclude, sistemi coinvolti (con link).
- `## Stato`: sintesi attuale in 2–4 righe, riscritta a ogni aggiornamento. La cronologia sta in `decision`, `meeting` e `risk`.
- `## Stakeholder`: persone e team coinvolti.
- `## Note`: valutazioni dell'utente.
