---
name: system
layer: knowledge
folder: knowledge/systems
fields:
  owner_team: {kind: link, to: team}
  criticality: {kind: enum, values: [low, medium, high]}
  status: {kind: enum, values: [active, deprecated, retired], closed: [retired]}
---
# System

Un sistema tecnico: servizio, applicazione, piattaforma, componente infrastrutturale.

**Crea** una pagina per i sistemi che compaiono in decisioni, rischi, incidenti o progetti.

**Non creare** pagine per librerie o componenti interni senza rilevanza manageriale.

**Struttura del corpo**:
- `## Cosa fa`: in 2–3 righe, per chi lo usa.
- `## Architettura`: dipendenze principali e tecnologie, con link ad altri `system`.
- `## Responsabilità`: team owner, on-call, contatti.
- `## Stato e debito tecnico`: problemi noti, con link a `risk` e `decision`.
- `## Note`: valutazioni dell'utente.
