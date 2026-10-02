---
name: schema
description: Mostra e fa evolvere lo schema della wiki Second Brain (elenca i tipi, presenta le proposte raccolte, aggiunge o modifica tipi e campi, applica migrazioni sulle pagine esistenti). Usa per "aggiungi un tipo vendor", "lo schema va cambiato", "che proposte di schema ci sono?".
argument-hint: "[proposals | add <tipo> | change <tipo> <modifica> | apply <id>]"
---

# /sb:schema: evoluzione dello schema

Argomenti: `$ARGUMENTS`

Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill.

Lo schema sta in `schema/`. I tipi `task` e `source-note` non si eliminano e non perdono i campi da cui dipende il toolkit:
- `task`: `status` (con `closed`), `owner`, `due`, `priority`, `related`;
- `source-note`: i campi comuni `external`, `version`, `synced`.

## Senza argomenti (solo lettura)

1. Per ogni layer elenca i tipi, con il numero di pagine (da `index.md`) e i campi principali.
2. Riporta il numero di proposte aperte, cioè le righe `- [ ]` in `schema/proposals.md`.

## `proposals`

Per ogni proposta aperta mostra:
1. il segnale osservato e le pagine coinvolte;
2. il **diff dello schema**: quali file di `schema/types/` cambiano e come;
3. il **piano di migrazione** sulle pagine (spostamenti, retitle, rinomina di campi, nuovi valori) con il numero di pagine toccate.

Per ciascuna chiedi se applicarla (`apply`), scartarla (segna `- [-]` e aggiungi il motivo) o rimandarla.

## `add <tipo>` / `change <tipo> <modifica>`

Raccogli ciò che manca, una domanda alla volta:
- layer;
- cartella (`<layer>/<plurale>`);
- campi (`kind`, `values`, `closed` per gli status, `to` per i link);
- campi obbligatori;
- prosa con **Crea**, **Non creare** e **Struttura del corpo**.

Registra il tutto come nuova proposta in `schema/proposals.md` e prosegui come `apply` su quella proposta.

## `apply <id>`

1. Mostra di nuovo il diff e il piano di migrazione, poi chiedi una conferma esplicita: è un'operazione distruttiva.
2. Modifica o crea i file in `schema/types/`.
3. Scrivi il piano in un file temporaneo (`mktemp`) nel formato del toolkit:

        {"ops": [
          {"op": "move", "path": "knowledge/topics/Acme.md", "to": "knowledge/vendors/Acme.md", "set": {"type": "vendor"}},
          {"op": "retitle", "path": "knowledge/people/Luca.md", "title": "Luca Bianchi"},
          {"op": "rename_field", "type": "person", "from": "role", "to": "position"},
          {"op": "set", "path": "operations/tasks/X.md", "fields": {"priority": "high", "owner": null}}
        ]}

   Se la proposta tocca solo lo schema e nessuna pagina, salta questo passo e il successivo.
4. Esegui `SB migrate <piano> --dry-run` e mostra le modifiche. Poi `SB migrate <piano>`.
5. Esegui `SB validate`. In caso di errori, correggi le pagine (per esempio valori da rimappare su un nuovo enum) e ripeti.
6. Segna la proposta `- [x]` in `schema/proposals.md`, con la data.
7. Esegui il flusso standard con `--op schema`, in un commit dedicato `sb(schema): P<n> <titolo>`.
