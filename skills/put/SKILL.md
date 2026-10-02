---
name: put
description: Fa entrare contenuti nella wiki Second Brain (note e dettati di 1:1 e riunioni, file locali come PDF e trascrizioni, pagine Confluence, ticket o query Jira, thread mail, link web), estraendo persone, decisioni, task e rischi e aggiornando le pagine giuste. Usa quando l'utente racconta qualcosa da ricordare ("ho fatto l'1:1 con…", "abbiamo deciso che…"), incolla note o chiede di importare, ingerire o salvare un contenuto.
argument-hint: "<testo | file | url | confluence:… | jira:… | mail:…> [--as <tipo>] [--plan]"
---

# /sb:put: fa entrare contenuti

Argomenti: `$ARGUMENTS`

## 0. Prima di iniziare

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.
2. Leggi `schema/layers.md` e `schema/sources.md`, ed elenca i tipi disponibili con `ls schema/types`.
3. Opzioni:
   - `--as <tipo>` fissa il tipo principale, che deve esistere in `schema/types`;
   - `--plan` obbliga a mostrare il piano prima di scrivere.
4. Se non c'è input, chiedi: "Cosa vuoi mettere nella wiki?".

## 1. Classifica l'input

| Input | Come riconoscerlo | Cattura |
|---|---|---|
| Testo libero | qualsiasi testo che non sia un riferimento | `raw/`, `kind: dictation` (`transcript` se è una trascrizione) |
| File o cartella | il percorso esiste | `raw/`, `kind: file`. Una cartella è un lotto, da trattare un file alla volta |
| Confluence | URL `…atlassian.net/wiki/…` oppure `confluence:<SPAZIO>/<id>` | source-note |
| Jira | `jira:<KEY>`, oppure `"jira: <JQL>"` (lotto) | source-note, una per ticket |
| Mail | `mail: <criterio di ricerca>` | source-note, una per thread |
| Web | URL http(s) | source-note |

Per le sorgenti esterne usa i tool MCP disponibili in sessione:
- Atlassian per pagine Confluence, issue Jira e ricerche JQL;
- Microsoft 365 per la mail;
- WebFetch per il web.

Se il tool necessario manca o fallisce, dillo e fermati per quella sorgente.

## 2. Cattura

**Grezzo.** Scrivi `raw/AAAA/MM/AAAA-MM-GG-<slug>.md`, con slug in minuscolo, a trattini e descrittivo:

    ---
    kind: dictation
    captured: 2026-10-02
    origin: chat
    ---
    <contenuto originale, intatto>

`origin` vale `chat` per il testo incollato o dettato, oppure il percorso del file originale. Per un file binario (PDF, DOCX…):
- copia il file accanto al `.md`, con lo stesso slug e l'estensione originale;
- metti nel `.md` il testo estratto. Per i PDF usa Read.

**Source-note** in `knowledge/sources/`:
- titolo `<Sistema> · <titolo del documento>`, senza i caratteri vietati;
- `external`: `confluence:<SPAZIO>/<pageId>`, `jira:<KEY>`, `mail:<id del thread>` oppure `url:<url>`;
- `version`: versione della pagina Confluence, `updated` del ticket Jira, data dell'ultimo messaggio;
- `synced`: oggi;
- corpo come da prosa del tipo `source-note`.

Se esiste già una source-note con lo stesso `external`, aggiornala seguendo le regole di `/sb:sync`, passo 3.

Se il sistema o lo scope (`confluence`, `jira`) non è registrato in `schema/sources.md`, chiedi se registrarlo. In caso affermativo aggiungi la voce `<id>: {system, scope, covers, stale_after_days}` e una riga di prosa. `url` e `mail` non si registrano.

## 3. Analisi

1. **Entità**: per ogni persona, team, progetto, sistema o fornitore menzionato esegui `SB resolve "<nome>"`, con `--type` se il tipo è chiaro. Applica le regole di ambiguità delle convenzioni.
2. **Estrai** ciò che conta per il management:
   - **fatti stabili** per il layer knowledge (ruoli, responsabilità, architetture, processi);
   - **eventi** per il layer operations: l'incontro stesso (`one-on-one`, `meeting`), le **decisioni**, i **rischi**, gli **obiettivi**;
   - **task**: impegni dell'utente ("devo…", "mi prendo…") e impegni altrui verso l'utente ("Luca mi manda…", "ho chiesto ad Anna di…");
   - **opinioni dell'utente**: valutazioni, preoccupazioni, giudizi. Vanno nella sezione `## Note` della pagina pertinente.
3. **Tipo principale**: fissato da `--as`, altrimenti dedotto. Un dettato su un incontro a due è un `one-on-one`.

## 4. Piano

Prepara l'elenco delle modifiche: pagina · crea o aggiorna · cosa cambia, in una riga.

**Mostralo e attendi conferma** se c'è `--plan` o se si verifica uno di questi casi:
- un'entità nuova somiglia a una esistente;
- il tipo è incerto;
- c'è un contrasto con una sorgente esterna;
- verrebbero toccate più di 15 pagine.

Altrimenti procedi.

## 5. Scrittura

Per ogni pagina rileggi la prosa del suo tipo in `schema/types/<tipo>.md` e seguila.

- **Knowledge (consolida)**: integra nella sezione giusta. Se una frase è superata, riscrivila invece di accodarne una nuova. Aggiorna `updated`. La cronologia sta nelle pagine operations.
- **Operations (crea)**: una pagina per evento o item, con titolo datato dove il tipo lo prevede (`2026-10-02 1on1 Luca Bianchi`).
- **Propagazione**: se un'informazione operativa cambia la conoscenza stabile, aggiorna anche la pagina knowledge e collega le due pagine.
- **Task**: segui le regole dei campi nella prosa del tipo `task`. Prima di crearne uno, controlla con `SB tasks list --view all --person "<persona>"` (o `--project`) che non esista già. Se esiste, aggiornalo e aggiungi la riga datata.
- **Citazioni**: ogni fatto rilevante porta `^[<fonte>]`. Aggiungi la fonte a `sources` di ogni pagina toccata.

## 6. Chiusura

Esegui il flusso standard delle convenzioni con `--op put`. Il messaggio è una sintesi, per esempio "1:1 Luca Bianchi: 2 task, 1 rischio".

Nei lotti (cartella, JQL, più riferimenti) esegui i passi 2–5 per ogni elemento e **un solo** passo 6 alla fine.

## 7. Riepilogo per l'utente (3–6 righe)

- **Creato**: pagine nuove, come wikilink.
- **Aggiornato**: pagine modificate.
- **Task**: titolo · owner · scadenza.
- **Dubbi**: cosa non hai potuto inferire o richiede una sua decisione.
- **Segnali di schema** registrati, se ce ne sono.
