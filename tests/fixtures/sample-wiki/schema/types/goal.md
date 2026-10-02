---
name: goal
layer: operations
folder: operations/goals
fields:
  period: {kind: string}
  status: {kind: enum, values: [planned, on-track, at-risk, off-track, achieved, missed, dropped], closed: [achieved, missed, dropped]}
  owner: {kind: link, to: person}
  project: {kind: link, to: project}
---
# Goal

Un obiettivo con un periodo: OKR, obiettivi di team o personali, impegni presi con il proprio manager.

**Crea** una pagina per ogni obiettivo formalizzato. `period` usa la forma `AAAA-Qn` o `AAAA`.

**Non creare** obiettivi per desideri non concordati: quelli vanno nelle `## Note` di una persona o di un team.

**Struttura del corpo**:
- `## Obiettivo e risultati chiave`: cosa, come si misura.
- `## Avanzamento`: una riga datata per ogni aggiornamento, con fonte.
- `## Rischi`: link alle pagine `risk`.
- `## Note`: valutazioni dell'utente.
