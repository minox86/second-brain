---
name: one-on-one
layer: operations
folder: operations/one-on-ones
fields:
  with: {kind: link, to: person}
  date: {kind: date}
required: [with, date]
---
# One-on-one

Un incontro individuale ricorrente tra l'utente e una persona.

**Crea** una pagina per ogni 1:1 di cui l'utente racconta o condivide le note. Titolo: `AAAA-MM-GG 1on1 <Nome Cognome>`.

**Non creare** un one-on-one per incontri a più persone (sono `meeting`) o per scambi rapidi senza contenuto.

**Struttura del corpo**:
- `## Temi`: punti discussi, con link a persone, progetti e topic.
- `## Umore e segnali`: stato d'animo, preoccupazioni, segnali di rischio (retention, burnout), riportati come l'utente li ha descritti.
- `## Impegni`: link ai task creati in entrambe le direzioni.
- `## Note`: valutazioni dell'utente.

Propaga nella pagina `person` solo ciò che cambia la conoscenza stabile (ruolo, aspirazioni, piano di crescita).
