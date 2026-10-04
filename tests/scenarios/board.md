# Scenari della board

Prepara una copia della wiki di esempio e avvia la board:

```bash
eval "$(tests/scenarios/setup.sh | grep -E '^(WIKI|REPO)=')"
python3 "$REPO/toolkit/sb.py" board --wiki "$WIKI"
```

`SB` sta per `python3 "$REPO/toolkit/sb.py" --wiki "$WIKI"`. In un secondo terminale, nella cartella `$WIKI`, esegui le verifiche.

## B1 · Triage nelle quattro viste
La board si apre sulla vista **Priorità**; i task di ogni colonna sono ordinati per scadenza.
1. Vista **Stato** (`1`): trascina "Preparare il budget Q4" in **Bloccati**.
2. Vista **Priorità** (`2`): trascina lo stesso task in **Media**.
3. Vista **Persone** (`3`): trascina "Ricevere da Luca la stima della migrazione DB" in **Io**.
4. Vista **Progetti** (`4`): c'è una colonna solo per i progetti con task aperti (più **Senza progetto** se serve); trascina il budget in un altro progetto.

Verifiche:
- `git log --format=%s -4` mostra quattro commit `sb(board): …`;
- `SB tasks list --view all` riporta `status: blocked` e `priority: medium` sul budget, il nuovo progetto tra i suoi `related` al posto del precedente, e nessun owner sulla stima;
- `SB validate` esce con 0.

## B2 · Creazione rapida in colonna
Vista Persone, colonna **Luca Bianchi**: "Aggiungi task", scrivi "Rivedere il piano on-call", poi Invio.

Verifiche:
- esiste `operations/tasks/Rivedere il piano on-call.md` con `owner: "[[Luca Bianchi]]"`;
- il pannello di dettaglio si apre sul nuovo task.

## B3 · Pannello di dettaglio
Sul task del budget:
- imposta la scadenza a una data;
- collega "Migrazione DB";
- aggiungi la nota "sentito il controllo di gestione".

Verifiche:
- il file contiene `- <oggi>: sentito il controllo di gestione` e `related` include `[[Migrazione DB]]`;
- i commenti e i campi non toccati sono rimasti identici (`git diff HEAD~3 -- "operations/tasks/Preparare il budget Q4.md"`).

## B4 · Conflitto con una modifica esterna
Con la board aperta, modifica a mano `operations/tasks/Preparare il budget Q4.md` (per esempio la priorità). Poi, **prima che passino 5 secondi**, chiudi il task dalla board.

Verifiche:
- la board mostra "Il task è stato modificato altrove" e si ricarica;
- la modifica esterna non è stata sovrascritta.

## B5 · Arresto con push
Aggiungi un remote nudo (`git init --bare /tmp/r.git && git remote add origin /tmp/r.git`), fai una modifica dalla board e premi Ctrl+C entro 60 secondi.

Verifiche:
- `git --git-dir /tmp/r.git log -1 --format=%s` mostra l'ultimo commit `sb(board): …`;
- `.sb/board.json` non esiste più.

## B6 · Da Claude Code
`/sb:board`, poi `/sb:board status`, poi `/sb:board stop`.

Verifiche:
- l'URL viene mostrato e il browser si apre;
- `status` riporta porta e stato del push;
- dopo `stop`, `.sb/board.json` non esiste più.
