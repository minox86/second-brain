# Second Brain

Questa cartella è una wiki **Second Brain** gestita dal plugin Claude Code `sb`.
Prima di creare o modificare pagine leggi lo schema in `schema/`:
- i tipi di pagina (`schema/types/`);
- la semantica dei layer (`schema/layers.md`);
- le sorgenti esterne (`schema/sources.md`).

La prosa dei file di schema è vincolante.

## Comandi

`/sb:status` · `/sb:put` · `/sb:sync` · `/sb:ask` · `/sb:prep` · `/sb:report` · `/sb:tasks` · `/sb:lint` · `/sb:schema`

Si attivano anche in linguaggio naturale ("ho fatto l'1:1 con…", "preparami la riunione di…", "cosa devo fare oggi?").

## Mappa

- `knowledge/`: conoscenza stabile (persone, team, progetti, sistemi, processi, temi, fornitori, sintesi delle fonti). Si consolida.
- `operations/`: eventi e item datati (task, 1:1, meeting, decisioni, obiettivi, rischi). Si crea e si chiude.
- `outputs/`: briefing e report generati.
- `raw/`: sorgenti grezze catturate. **Immutabile.**
- `index.md`: indice generato, da non modificare a mano.
- `log.md`: registro delle operazioni, solo in aggiunta.

## Regole

- Nome del file = titolo. I wikilink puntano sempre al titolo canonico: `[[Titolo]]` o `[[Titolo|alias]]`.
- Nessun fatto senza fonte (`^[raw/…]`, `^[confluence:…]`, …) e nessun campo inventato.
- Mai modificare `raw/`.
- Le sezioni `## Note` raccolgono le opinioni dell'utente: un re-ingest non le sovrascrive mai.
- Le sorgenti esterne sono autorevoli sui fatti che documentano; la wiki ne è la rielaborazione strutturata.
- Ogni modifica termina con validate → index → log → commit → push.
- Le operazioni distruttive (spostamenti, merge, cancellazioni, migrazioni) richiedono una conferma esplicita e un commit dedicato.
- Dopo una modifica fatta a mano alle pagine, esegui `/sb:lint`.
