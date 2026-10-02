---
name: prep
description: Prepara e archivia un briefing per un 1:1, una riunione, una persona o un progetto partendo dalla wiki Second Brain. Usa per "preparami l'1:1 con Luca", "cosa devo sapere per la riunione di domani con il team X?", "fammi il punto sul progetto Y".
argument-hint: "<persona | meeting | progetto | team> [--for <data>]"
---

# /sb:prep: briefing

Argomenti: `$ARGUMENTS`

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.
2. **Target**: esegui `SB resolve "<target>"`; se è ambiguo, chiedi. `--for` accetta una data o un'espressione ("domani", "lunedì") da convertire in data assoluta; il default è oggi.
3. **Template**: scegli in `schema/briefings/` in base al tipo del target. Nel preset:

   | Target | Template |
   |---|---|
   | persona con pagine `one-on-one` | `one-on-one.md` |
   | meeting o serie ricorrente | `meeting.md` |
   | persona senza 1:1 | `person.md` |
   | progetto o team | `project.md` |

   Se nessun template è adatto, usa la struttura di `project.md`. Leggi il template e seguine sezioni e finestra temporale.
4. **Raccogli**:
   - la pagina del target e i suoi backlink (`.sb/backlinks.json`);
   - i task: `SB tasks list --view all --person "<target>"` per una persona, `--project "<target>"` per un progetto. Tieni quelli aperti e quelli chiusi nella finestra;
   - le pagine operations collegate (1:1, meeting, decisioni, rischi, obiettivi), dalla più recente;
   - le source-note collegate, segnalando quelle stantie secondo `SB sources stale`;
   - l'ultimo briefing sullo stesso target in `outputs/briefings/`, per dire cosa è cambiato da allora.
5. **Scrivi** `outputs/briefings/Briefing AAAA-MM-GG <Titolo del target>.md`, con la data di `--for`. Se il file esiste già, aggiornalo.

        ---
        type: briefing
        title: Briefing 2026-10-03 Luca Bianchi
        about: "[[Luca Bianchi]]"
        for: 2026-10-03
        created: 2026-10-02
        ---
        <sezioni del template; ogni punto con il [[link]] alla pagina da cui viene>

6. Mostra in chat il briefing completo, non un riassunto. Poi esegui il flusso standard con `--op prep`.
