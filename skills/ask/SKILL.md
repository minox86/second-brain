---
name: ask
description: Risponde a domande puntuali usando la wiki Second Brain, con citazioni a pagine e fonti, e va sulle sorgenti live (Confluence, Jira) solo se serve. Usa per domande come "cosa abbiamo deciso su X?", "quando ho parlato con Y di Z?", "chi segue W?".
argument-hint: "<domanda> [--live]"
---

# /sb:ask: domanda puntuale

Domanda: `$ARGUMENTS`

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.
2. **Orientati**: leggi `index.md` ed esegui `SB resolve "<nome>"` per ogni entità della domanda.
3. **Cerca**, dal più specifico al più ampio:
   1. le pagine delle entità risolte e i loro backlink (`.sb/backlinks.json`; se manca, esegui `SB index`);
   2. `grep -ril "<parole chiave>" knowledge operations outputs`;
   3. per le domande sul "quando", le pagine operations ordinate per data (titolo datato o campo `date`).
4. **Fonte live**: interroga Confluence o Jira via MCP solo se c'è `--live`, oppure se la wiki non basta e una source-note o `schema/sources.md` indicano dove sta il dettaglio. Se la fonte non è raggiungibile, dillo.
5. **Rispondi**:
   - prima la risposta diretta, in 1–5 frasi;
   - poi le evidenze, ognuna con `[[Pagina]]` e la fonte originale se la pagina la cita (`^[…]`);
   - tieni distinti i fatti dalle opinioni dell'utente (sezioni `## Note`);
   - se la wiki non contiene la risposta, dillo chiaramente e suggerisci cosa ingerire (`/sb:put …`).
6. **Non archiviare.** Se l'utente chiede di salvare la risposta ("salvala" o simile):
   - crea `outputs/reports/Report AAAA-MM-GG risposta <argomento breve>.md` con `type: report`, `kind: answer`, `scope: <argomento>`, `created`;
   - nel corpo metti domanda, risposta ed evidenze;
   - esegui il flusso standard con `--op ask`.
