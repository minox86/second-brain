---
name: lint
description: Manutenzione della wiki Second Brain che cerca link rotti, pagine orfane, campi non validi, sorgenti stantie, task scaduti, item fermi, duplicati, contraddizioni e pagine da consolidare, e corregge con --fix. Usa per "fai pulizia nella wiki", "controlla la wiki", "ci sono problemi nella wiki?".
argument-hint: "[--fix] [--only structural|semantic]"
---

# /sb:lint: manutenzione

Argomenti: `$ARGUMENTS`

Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill. Senza `--fix` la skill è **solo lettura**: non scrive file e non fa commit.

## 1. Controlli strutturali

Salta se c'è `--only semantic`.

Esegui `SB lint`. Raggruppa le issue per codice e mostra per ciascun gruppo il conteggio e fino a 5 pagine.

## 2. Controlli semantici

Salta se c'è `--only structural`.

Parti da `index.md` e dalle pagine aggiornate di recente, e cerca:
- **duplicati probabili**: pagine dello stesso tipo con titoli simili (`SB resolve "<titolo>" --type <tipo>` con altri candidati sopra 0.5) o con contenuti sovrapposti;
- **contraddizioni**: fatti incompatibili tra pagine (ruoli, date, responsabili, stato di un progetto);
- **fatti superati**: pagine che citano una source-note con `synced` più recente dell'`updated` della pagina;
- **pagine da consolidare**: pagine knowledge con cronologie accodate invece di sezioni stabili, o più lunghe di circa 150 righe;
- **segnali di schema**: `unknown-field` ricorrenti, tipi generici usati sempre con la stessa struttura, campi che mancano.

Per ogni rilievo mostra le pagine coinvolte e la correzione proposta.

## 3. Correzioni

Solo con `--fix`.

1. **Meccaniche**: applicale subito, tutte in un unico commit.
   - `alias-link`: riscrivi `[[alias]]` come `[[Titolo|alias]]`.
   - `filename-mismatch` e `wrong-folder`: operazione `move` verso `<folder del tipo>/<title>.md` con `SB migrate`.
   - Date non ISO convertibili senza ambiguità.

   Poi esegui il flusso standard con `--op lint`.
2. **Semantiche**: una alla volta. Proponi la correzione e attendi un sì esplicito.
   - Unire due duplicati è un'operazione distruttiva. Fondi i contenuti nella pagina che resta, poi usa `retitle` o `move` con `SB migrate` per riallineare i link, ed elimina la pagina assorbita con `git rm`. Fai un commit dedicato.
   - Una contraddizione si risolve con le regole delle sorgenti: sui fatti vince la fonte esterna, le note dell'utente non si toccano.
3. **Segnali di schema**: registrali in `schema/proposals.md` nel formato delle convenzioni e indica `/sb:schema proposals`.

## 4. Riepilogo

Riporta i conteggi prima e dopo, le correzioni applicate e i rilievi rimasti aperti.
