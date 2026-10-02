---
name: sync
description: Riallinea la wiki Second Brain con le sorgenti esterne (Confluence, Jira e simili) trovando le source-note stantie o cambiate e rielaborando solo ciò che è cambiato. Usa per "aggiorna da Confluence", "riallinea le sorgenti", "cosa è cambiato nelle fonti?".
argument-hint: "[<source-id> | <pagina> | --all] [--check]"
---

# /sb:sync: riallinea le sorgenti esterne

Argomenti: `$ARGUMENTS`

## 0. Prima di iniziare

Leggi `BASE/../../references/conventions.md` (BASE è la base directory di questa skill) e `schema/sources.md`.

## 1. Candidati

1. Esegui `SB sources stale` per trovare le source-note oltre la soglia o mai sincronizzate.
2. Scegli l'insieme da verificare in base all'argomento:
   - `<source-id>`: tutte le source-note il cui `external` appartiene a quella sorgente (stesso sistema e scope; cercale con `grep -rlE 'external: "?<system>:<SCOPE>' knowledge/sources`, perché il valore può essere scritto con o senza virgolette);
   - `<pagina>`: `SB resolve "<pagina>" --type source-note`;
   - `--all` o nessun argomento: le stantie del punto 1.
3. Per ogni candidata leggi via MCP la versione attuale (versione della pagina Confluence, `updated` del ticket Jira) e confrontala con `version`. Classifica ciascuna come:
   - **cambiata**: la versione è diversa;
   - **invariata**: la versione è la stessa;
   - **irraggiungibile**: errore o tool mancante.

## 2. Report

Mostra una tabella: titolo · sistema · età · esito. Poi:
- con `--check`: fermati qui, senza scritture e senza commit;
- senza argomenti: chiedi quali delle cambiate rielaborare (default: tutte);
- con `<source-id>`, `<pagina>` o `--all`: procedi con tutte le cambiate.

## 3. Rielaborazione, per ogni source-note scelta

1. **Invariata**: aggiorna solo `synced` alla data di oggi.
2. **Cambiata**: leggi il contenuto attuale e individua cosa è cambiato rispetto alla sintesi. Aggiorna la source-note: sintesi, `version`, `synced`, `updated`.
3. Propaga **solo i fatti cambiati** nelle pagine che citano quella sorgente (`grep -rl "<external>" knowledge operations`):
   - un fatto derivato da questa sorgente si aggiorna e la citazione resta;
   - se il fatto nuovo contrasta con un contenuto che **non** deriva da questa sorgente (una nota dell'utente o un'altra fonte), non sovrascriverlo. Aggiungi accanto `> ⚠️ In contrasto con ^[<external>] (sync del AAAA-MM-GG): <fatto nuovo>` e riportalo nel riepilogo;
   - le sezioni `## Note` non si toccano mai.
4. Le source-note con `authority: migrated` si saltano sempre.
5. Le pagine nuove comparse nello spazio esterno non sono compito di sync: per ingerirle si usa `/sb:put`.

## 4. Chiusura

Esegui il flusso standard con `--op sync`. Messaggio: "N sorgenti riallineate, M pagine aggiornate, K conflitti".

Nel riepilogo elenca le cambiate, le invariate, le irraggiungibili e i conflitti da guardare.
