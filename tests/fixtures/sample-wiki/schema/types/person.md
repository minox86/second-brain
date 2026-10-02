---
name: person
layer: knowledge
folder: knowledge/people
fields:
  role: {kind: string}
  relationship: {kind: enum, values: [report, skip-report, peer, manager, stakeholder, external]}
  team: {kind: link, to: team}
  reports_to: {kind: link, to: person}
  status: {kind: enum, values: [active, left], closed: [left]}
---
# Person

Una persona con cui lavori: riporti diretti e indiretti, peer, il tuo manager, stakeholder, contatti esterni.

**Crea** una pagina quando una persona compare in modo ricorrente o ha un ruolo attivo in un progetto, una decisione, un task o un 1:1.

**Non creare** una pagina per menzioni di passaggio: scrivi solo il nome nel testo, senza link.

**Struttura del corpo** (si aggiorna e si consolida, non si accoda):
- `## Ruolo e contesto`: cosa fa, in quale team, da quanto, punti di forza.
- `## Obiettivi e crescita`: aspirazioni, piano di sviluppo, feedback, ognuno con data e fonte.
- `## Temi aperti`: questioni in corso, ognuna collegata alla pagina operativa (1:1, task, rischio).
- `## Note`: osservazioni e valutazioni dell'utente. Il re-ingest non le tocca mai.

`relationship` è il rapporto con l'utente. La cronologia degli incontri sta nelle pagine `one-on-one` e `meeting`. Quando una persona lascia l'azienda, imposta `status: left` e non cancellare la pagina.
