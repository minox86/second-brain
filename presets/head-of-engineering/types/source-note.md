---
name: source-note
layer: knowledge
folder: knowledge/sources
---
# Source note

La sintesi di un documento esterno o di una cattura: pagina Confluence, ticket Jira, thread mail, articolo web. È il ponte tra la sorgente e le pagine tipizzate.

**Crea** una source-note per ogni documento esterno ingerito, una sola per riferimento `external`.

**Non creare** source-note per le catture conservate in `raw/` (dettati, file locali): il grezzo è già la fonte.

**Struttura del corpo**:
- `## Sintesi`: 5–20 righe sui punti rilevanti per il management.
- `## Pagine collegate`: le pagine tipizzate in cui sono stati propagati i fatti.

Campi comuni obbligatori nella pratica:
- `external`: riferimento alla sorgente;
- `version`: versione della pagina, `updated` del ticket, data dell'ultimo messaggio;
- `synced`: data dell'ultimo allineamento.

Titolo: `<Sistema> · <titolo del documento>`. Con `authority: migrated` la wiki diventa fonte di verità e la sorgente non si re-ingerisce più.
