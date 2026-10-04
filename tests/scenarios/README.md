# Scenari di accettazione delle skill

Le skill sono istruzioni per Claude: si verificano eseguendole su una wiki di prova e controllando il risultato con il toolkit. Ogni scenario parte da una copia pulita:

```bash
eval "$(tests/scenarios/setup.sh | grep -E '^(WIKI|REPO)=')"
cd "$WIKI" && claude --plugin-dir "$REPO"
```

In un secondo terminale, nella stessa cartella `$WIKI`, esegui le verifiche. `SB` sta per `python3 "$REPO/toolkit/sb.py"`.

## S1 · `/sb:put` di un 1:1 (estrazione, deduplica dei task, citazioni)

Comando:

    /sb:put --as one-on-one 1:1 con Luca oggi. Vuole crescere verso staff engineer entro un anno. È preoccupato per i turni di on-call del team Platform. Conferma che mi manda la stima della migrazione DB entro venerdì. Io devo parlare con Anna del budget per l'on-call.

Verifiche:
- `SB validate` → exit 0.
- `ls operations/one-on-ones/` → c'è un nuovo `<oggi> 1on1 Luca Bianchi.md` con `with: "[[Luca Bianchi]]"`.
- `SB tasks list --view all --person "Luca Bianchi"` → **un solo** task sulla stima della migrazione (quello esistente, aggiornato), con `due` = il prossimo venerdì.
- `SB tasks list --view mine` → c'è un task nuovo sul budget per l'on-call, senza owner, con `[[Anna Neri]]` in `related`.
- `ls raw/$(date +%Y/%m)/` → c'è il dettato catturato.
- `knowledge/people/Luca Bianchi.md` → l'aspirazione a staff engineer è in "Obiettivi e crescita", con `^[raw/…]`.
- `git log -1 --format=%s` → inizia con `sb(put):`, e `git status --porcelain` è vuoto.

## S2 · `/sb:ask` (risposta citata, nessuna scrittura)

Comando: `/sb:ask chi guida il team Platform e su cosa sta lavorando?`

Verifiche:
- la risposta cita `[[Luca Bianchi]]`, `[[Platform]]` e `[[Migrazione DB]]`;
- `git status --porcelain` è vuoto e `git log -1 --format=%s` è ancora `fixture`.

## S3 · `/sb:prep` (briefing archiviato)

Comando: `/sb:prep Luca Bianchi`

Verifiche:
- esiste `outputs/briefings/Briefing <oggi> Luca Bianchi.md` con `type: briefing` e `about: "[[Luca Bianchi]]"`;
- il briefing contiene il task sulla stima e le sezioni del template `one-on-one`;
- `SB validate` → exit 0; `git log -1 --format=%s` inizia con `sb(prep):`.

## S4 · `/sb:tasks` (vista in sola lettura, poi chiusura)

Comandi: `/sb:tasks`, poi `/sb:tasks done budget Q4`

Verifiche:
- dopo il primo comando, `git status --porcelain` è vuoto;
- dopo il secondo, `operations/tasks/Preparare il budget Q4.md` ha `status: done` e una riga `- <oggi>: chiuso`;
- `SB tasks list --view mine` non lo mostra più; `git log -1 --format=%s` inizia con `sb(tasks):`.

## S5 · `/sb:lint` e `/sb:lint --fix`

Setup:

    printf -- '---\ntype: topic\ntitle: On-call\n---\nNe parla spesso [[Luca]].\n' > knowledge/topics/On-call.md && git add -A && git commit -qm "setup S5"

Comandi: `/sb:lint`, poi `/sb:lint --fix`

Verifiche:
- dopo il primo comando, il report include `alias-link` per `On-call.md` e la source-note stantia; `git status --porcelain` è vuoto;
- dopo `--fix`, `On-call.md` contiene `[[Luca Bianchi|Luca]]` e `SB validate` non riporta più `alias-link`; `git log -1 --format=%s` inizia con `sb(lint):`.

## S6 · `/sb:schema add` (nuovo tipo + proposta applicata)

Comando: `/sb:schema add customer`. Rispondi: layer knowledge, cartella `knowledge/customers`, campo `account_manager` (link a person), nessun campo obbligatorio.

Verifiche:
- esiste `schema/types/customer.md` con `folder: knowledge/customers`;
- `schema/proposals.md` contiene una voce `- [x]`;
- `SB validate` → exit 0; `git log -1 --format=%s` inizia con `sb(schema):`.

## S7 · `/sb:sync --check` (sorgente irraggiungibile o inesistente)

Comando: `/sb:sync --check`

Verifiche:
- il report elenca `Confluence · Incident Management` come stantia, con esito "irraggiungibile" (la pagina di esempio non esiste) o "invariata/cambiata" se l'MCP risponde;
- in ogni caso `git status --porcelain` è vuoto.

## S8 · `/sb:init` (intervista + scaffold)

Setup: `T="$(mktemp -d)" && cd "$T" && git init -q -b main && claude --plugin-dir "$REPO"`

Comando: `/sb:init`. Rispondi all'intervista con un contesto inventato: 2 team e 3 persone, nessun remote.

Verifiche:
- `SB validate --wiki "$T"` → exit 0;
- esistono `schema/types/task.md`, `CLAUDE.md` e le pagine seed delle persone indicate;
- `git -C "$T" log -1 --format=%s` inizia con `sb(init):`.

## S9 · `/sb:meeting` (richiede il connettore Microsoft 365 e un calendario reale)

Comandi, uno per volta:
- `/sb:meeting` → la lista di oggi esclude annullate, blocchi orari e pause; le riunioni già catturate compaiono come non selezionabili.
- `/sb:meeting <link teams.microsoft.com/meet/… di una riunione trascritta>`.
- "aggiungi la riunione appena finita" → chiede conferma con oggetto e orario prima di procedere.
- `/sb:meeting <nome di una riunione senza trascrizione>` → chiede il dettato; "salta" la esclude.

Verifiche:
- `ls raw/<anno>/<mese>/` → un grezzo per riunione con `origin: teams:event/…`; la sezione `## Trascrizione` contiene il WEBVTT;
- `SB meeting seen <id>` → restituisce il percorso del grezzo; un secondo `/sb:meeting` sulla stessa riunione la segnala come già catturata;
- `SB validate` → exit 0; esiste la pagina `meeting` o `one-on-one` con `## Note` vuota;
- `ls .sb/tmp/` → nessun file `meeting-*`;
- `git log -1 --format=%s` inizia con `sb(meeting):` e `git status --porcelain` è vuoto.
