# Convenzioni comuni delle skill `sb`

Ogni skill del plugin legge questo file prima di agire. BASE è la *base directory* della skill, indicata quando la skill viene caricata. La radice del plugin è `BASE/../..`.

## Toolkit

    SB = python3 "BASE/../../toolkit/sb.py"

- Ogni comando stampa JSON su stdout. Exit `0` = ok; `1` = problemi trovati, descritti nel JSON; `2` = errore d'uso o d'ambiente (leggi il campo `error`).
- Si lancia dalla radice della wiki o da una sua sottocartella. Altrimenti si passa `--wiki <cartella>`.
- `SB version` ritorna `wiki`: il percorso della wiki corrente, oppure `null` se non sei in una wiki. In quel caso, per ogni comando tranne `init`, fermati e proponi `/sb:init`.
- Non rifare a mano ciò che fa il toolkit: validazione, indice, risoluzione dei nomi, query sui task, sorgenti stantie, lint strutturale, migrazioni, log.

| Comando | Uso |
|---|---|
| `SB validate [pagine…]` | Controlla le pagine contro lo schema |
| `SB index` | Rigenera `index.md` e `.sb/backlinks.json` |
| `SB resolve "<nome>" [--type T]` | Trova le pagine candidate per un nome |
| `SB tasks list --view V [--project P] [--person P] [--priority X]` | Elenca i task (viste: mine, delegated, overdue, today, week, blocked, all) |
| `SB sources stale` | Elenca le source-note da riallineare |
| `SB lint` | Esegue i controlli strutturali |
| `SB status` | Raccoglie i dati del cruscotto |
| `SB migrate <piano.json> [--dry-run]` | Esegue spostamenti, retitle, rinomina e modifica di campi |
| `SB log "<messaggio>" --op <skill>` | Aggiunge una riga a `log.md` |
| `SB scaffold <schema-dir> <cartella>` | Crea una nuova wiki |

## Prima di scrivere

Leggi `schema/layers.md`, i file `schema/types/<tipo>.md` dei tipi che userai e `schema/sources.md` se tocchi sorgenti esterne. La prosa dei tipi è vincolante: dice quando creare una pagina, quando non crearla e come strutturarne il corpo.

## Formato delle pagine

- Nome del file = `title` + `.md`, nella cartella `folder` del tipo. I titoli non contengono `\ / : * ? " < > | # ^ [ ]`: scrivi "1on1" e non "1:1", usa "·" o "-" come separatori.
- I wikilink puntano sempre al titolo canonico: `[[Luca Bianchi]]`, oppure `[[Luca Bianchi|Luca]]` per mostrare un alias. Nel frontmatter i link vanno tra virgolette: `owner: "[[Luca Bianchi]]"`, `related: ["[[A]]", "[[B]]"]`.
- Le date sono in formato ISO `AAAA-MM-GG`. Converti sempre le espressioni relative ("venerdì", "fine mese") rispetto alla data dell'evento.
- Metti tra virgolette le stringhe del frontmatter che contengono `, ` `: ` ` #` o che iniziano con un simbolo.
- Citazioni: ogni fatto rilevante porta `^[<fonte>]`, dove fonte è il percorso di un file in `raw/` senza `.md` (`raw/2026/10/2026-10-02-1on1-luca`) o un riferimento esterno (`confluence:ENG/123`, `jira:PLAT-42`, `url:https://…`, `mail:<id>`). Le stesse fonti vanno nella lista `sources` del frontmatter.
- `created` va impostato alla creazione, `updated` a ogni modifica sostanziale.

## Ambiguità

Per ogni entità menzionata esegui `SB resolve "<nome>"`.

- Un candidato con `match` `title` o `alias` è quello giusto: usalo.
- Un solo candidato `partial` (punteggio 0.75) e nessun altro sopra 0.5: usalo.
- Più candidati, oppure solo `fuzzy`: chiedi all'utente con una sola domanda a scelta multipla, includendo l'opzione "nuova pagina". Poi aggiungi il nome usato agli `aliases` della pagina scelta.
- Nessun candidato: è un'entità nuova. Creala solo se la prosa del tipo lo prevede; altrimenti scrivi il nome come testo semplice.

## Regole non negoziabili

- Nessun fatto senza fonte. Nessun campo inventato: se non è inferibile con ragionevole sicurezza, omettilo.
- Mai modificare i file in `raw/` dopo la cattura.
- Le sezioni `## Note` raccolgono opinioni e valutazioni dell'utente: un re-ingest non le sovrascrive mai.
- Le source-note con `authority: migrated` non si re-ingeriscono.
- Un task dell'utente non ha `owner`. `owner` indica solo un'altra persona.
- Se una fonte esterna non è raggiungibile (tool MCP assente o in errore), dillo e fermati su quella fonte. Non ricostruire contenuti a memoria.
- Le operazioni distruttive (spostamenti di massa, merge, cancellazioni, migrazioni di schema) richiedono una conferma esplicita e un commit dedicato.

## Flusso di chiusura

Ogni operazione che scrive termina così, nella radice della wiki:

1. `SB validate <pagine create o modificate>`. In caso di errori, correggi e ripeti, al massimo due volte. Se restano errori, procedi comunque: elenca le pagine problematiche nel riepilogo e nel messaggio di log.
2. `SB index`
3. `SB log "<sintesi in una riga>" --op <skill>`
4. `git add -A && git commit -m "sb(<skill>): <sintesi>"`
5. Se esiste un remote (`git remote` non vuoto): `git push`. Se il push fallisce, non ritentare in loop: segnalalo nel riepilogo, il commit resta locale e `/sb:status` lo mostrerà.

Non lasciare mai la wiki con modifiche non committate.

## Segnali di schema

Quando lo schema non basta, aggiungi una voce in fondo a `schema/proposals.md`, con `n` = numero massimo esistente + 1. Esempi: la stessa struttura ripetuta in un tipo generico, un campo che manca, `unknown-field` ricorrenti.

    - [ ] P<n> · <titolo breve>
      - segnale: <cosa hai osservato, con i link alle pagine>
      - proposta: <modifica allo schema>

Non modificare `schema/types/` fuori da `/sb:schema` o `/sb:init`.
