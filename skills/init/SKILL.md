---
name: init
description: Crea una nuova wiki Second Brain con un'intervista che genera lo schema su misura, partendo dal preset Head of Engineering. Usa quando l'utente vuole creare o inizializzare un second brain o una nuova wiki, o quando un comando sb viene lanciato fuori da una wiki.
argument-hint: "[path]"
---

# /sb:init: crea una wiki

Argomenti: `$ARGUMENTS`. Contiene il percorso opzionale della nuova wiki; il default è la directory corrente.

## 0. Prima di iniziare

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill. Da qui in poi `PRESET` = `BASE/../../presets/head-of-engineering`.
2. Determina la cartella di destinazione `TARGET`.
   - Se `SB version --wiki TARGET` ritorna `wiki` non nullo, è già una wiki: fermati e proponi `/sb:status`.
   - Se `TARGET` contiene file diversi da `.git` e `.DS_Store`, fermati e chiedi un'altra cartella. Non sovrascrivere mai nulla.

## 1. Intervista

Una domanda per messaggio, preferibilmente a scelta multipla, con risposte brevi. Ogni 2–3 risposte riassumi ciò che hai capito. Gli argomenti, in quest'ordine:

1. **Contesto**: azienda o unità, ruolo, perimetro (quanti team, quante persone), e il **nome** da dare alla wiki: compare in alto nella board. Il default è il nome della cartella.
2. **Persone e team**: riporti diretti, team con i loro lead, il tuo manager, i peer chiave. Raccogli nomi e cognomi: diventeranno le prime pagine.
3. **Ritmi**: cadenza dei 1:1, da cui ricavi `one_on_one_gap_days` (cadenza + circa il 50%); meeting ricorrenti importanti; rituali (planning, review, staff meeting).
4. **Sorgenti esterne**: spazi Confluence e progetti Jira rilevanti. Per ciascuno chiedi la chiave, a cosa serve e ogni quanto cambia, da cui ricavi `stale_after_days`. Chiedi anche se usa mail e calendario. Verifica quali tool MCP (Atlassian, Microsoft 365) sono disponibili in questa sessione e dillo.
5. **Cosa vuoi ritrovare**: le 3–5 domande che vorresti poter fare alla wiki. Servono ad adattare tipi, briefing e report.
6. **Tipi**: mostra i tipi del preset per layer, una riga ciascuno, ricavata dai file in `PRESET/types/`. Chiedi cosa rinominare, aggiungere o togliere. `task` e `source-note` sono obbligatori.
7. **Repository**: URL del remote git (o nessuno per ora) e branch (default `main`).

## 2. Proposta di schema

1. Crea una cartella temporanea (`mktemp -d`) e copia il preset: `cp -R "PRESET" "<tmp>/schema"`.
2. Modifica la copia secondo le risposte:
   - `wiki.md`: crealo con il frontmatter `name: <nome scelto>` (più una riga di prosa) se l'utente ha dato un nome diverso da quello della cartella;
   - `layers.md`: le soglie;
   - `sources.md`: una voce di frontmatter per sorgente (`<id>: {system: …, scope: <CHIAVE>, covers: [tipi], stale_after_days: N}`) e una sezione di prosa per ciascuna;
   - `types/*.md`: rinomina, aggiungi o togli tipi; adatta la prosa al contesto reale (nomi dei team, rituali). Un tipo nuovo segue lo stesso formato degli altri: frontmatter `name`, `layer`, `folder` (= `<layer>/<plurale>`), `fields`, `required`, poi la prosa con **Crea**, **Non creare** e **Struttura del corpo**;
   - `briefings/` e `reports/`: adatta le sezioni alle domande del punto 1.5.
3. Mostra la proposta in modo compatto: tipi per layer, sorgenti, soglie, briefing, report. Chiedi conferma e applica le correzioni finché l'utente non approva.

## 3. Creazione

1. Esegui `SB scaffold "<tmp>/schema" "TARGET"`. Se esce con 2, mostra `error`, correggi lo schema temporaneo e riprova.
2. **Seed**:
   - cattura le risposte dell'intervista utili come fonte in `raw/AAAA/MM/AAAA-MM-GG-init-intervista.md` (`kind: dictation`);
   - crea le pagine `person` e `team` raccolte al punto 1.2, con i soli fatti dichiarati dall'utente e la citazione a quel file.
3. **Git** nella cartella `TARGET`:
   - se manca `.git`: `git init -b <branch>`;
   - se c'è un remote e non esiste `origin`: `git remote add origin <url>`.
4. Chiudi con il flusso standard delle convenzioni (`--op init`). Per il primo push usa `git push -u origin <branch>`.

## 4. Riepilogo

In 5–8 righe:
- dove sta la wiki;
- i tipi creati;
- le pagine seed;
- l'esito del push.

Poi suggerisci i primi passi:
- aprire Claude Code dentro la wiki;
- `/sb:put` per il primo 1:1 o documento;
- `/sb:status`.
