---
name: status
description: Cruscotto della wiki Second Brain con task scaduti e in scadenza, delegati in ritardo, 1:1 trascurati, sorgenti da riallineare, proposte di schema, problemi di lint e stato git. Usa per "com'è messa la wiki?", "cosa ho in sospeso?", "da dove comincio oggi?".
---

# /sb:status: cruscotto

Solo lettura: non scrivere file e non fare commit.

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.
2. Esegui `SB status`. Se esce con 2 perché la cartella non è una wiki, proponi `/sb:init`.
3. Controlla lo stato git:
   - `git status --porcelain` per le modifiche non committate;
   - se esiste un upstream, `git rev-list --count @{u}..HEAD` per i commit non pushati.
4. Mostra al massimo 15 righe. Includi **solo le sezioni non vuote**, in quest'ordine:
   - **Scaduti** (tuoi): titolo · scadenza · priorità
   - **In scadenza** (entro `due_soon_days`): titolo · scadenza
   - **Delegati in ritardo**: titolo · owner · scadenza
   - **1:1 da fare**: persona · giorni dall'ultimo
   - **Sorgenti da riallineare**: titolo · età in giorni, oppure "mai sincronizzata"
   - **Proposte di schema aperte**: numero
   - **Lint**: errori · avvisi
   - **Git**: modifiche non committate · commit non pushati

   Se una sezione ha più di 3 elementi, mostra i primi 3 e "+N".
5. Chiudi con 1–3 azioni suggerite, concrete e legate a ciò che hai mostrato. Esempi: `/sb:prep Luca Bianchi`, `/sb:sync`, `/sb:lint --fix`, `git push`. Se è tutto in ordine, dillo in una riga.
