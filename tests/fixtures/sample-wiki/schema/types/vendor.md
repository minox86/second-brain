---
name: vendor
layer: knowledge
folder: knowledge/vendors
fields:
  contact: {kind: link, to: person}
  contract_end: {kind: date}
  status: {kind: enum, values: [evaluating, active, ended], closed: [ended]}
---
# Vendor

Un fornitore esterno: software, servizi, consulenza, staffing.

**Crea** una pagina quando un fornitore ha un contratto attivo o è in valutazione.

**Non creare** pagine per strumenti usati senza un rapporto commerciale da gestire.

**Struttura del corpo**:
- `## Cosa forniscono`: servizio, perimetro, team che lo usano.
- `## Contratto`: scadenze, rinnovi, costi se noti (con fonte).
- `## Rapporto`: qualità, problemi, escalation, con link alle pagine operations.
- `## Note`: valutazioni dell'utente.
