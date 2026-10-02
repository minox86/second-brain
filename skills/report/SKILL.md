---
name: report
description: Produce e archivia sintesi trasversali dalla wiki Second Brain (settimana, mese, rischi, carico del team, update per il proprio manager, cose delegate). Usa per "riepilogo della settimana", "quali rischi abbiamo?", "come sta il carico del team?", "preparami l'update per il mio capo".
argument-hint: "<tipo> [--scope <entità>] [--period <periodo>]"
---

# /sb:report: sintesi trasversale

Argomenti: `$ARGUMENTS`

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.
2. **Tipo**: corrisponde a un file in `schema/reports/` (`ls schema/reports`). Se il tipo manca o non esiste, mostra quelli disponibili con il loro titolo e chiedi.
3. **Periodo e scope**:
   - `--period` accetta `AAAA-MM`, `AAAA-Www`, `AAAA-MM-GG..AAAA-MM-GG` o espressioni ("settimana scorsa"). Il default è nel template;
   - `--scope` va risolto con `SB resolve`. Senza scope il report copre tutta la wiki.
4. **Raccogli** secondo il template:
   - le righe di `log.md` nel periodo, per sapere cosa è entrato;
   - le pagine create o aggiornate nel periodo (`created`, `updated` o data nel titolo);
   - i task con la vista adatta (`SB tasks list --view all|delegated|overdue`);
   - rischi, decisioni e obiettivi pertinenti allo scope.
5. **Scrivi** `outputs/reports/Report AAAA-MM-GG <tipo>[ <scope>].md`:
   - frontmatter: `type: report`, `title`, `kind: <tipo>`, `scope` (se presente), `period`, `created`;
   - corpo secondo il template, con ogni affermazione collegata alla pagina d'origine.
6. Mostra in chat il report completo. Poi esegui il flusso standard con `--op report`.
