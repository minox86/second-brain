---
name: meeting
description: Fa entrare nella wiki Second Brain le riunioni Teams scaricando da Microsoft 365 evento, partecipanti, trascrizione e chat. Usa quando l'utente chiede di aggiungere o ingerire una riunione ("aggiungi la riunione appena finita", "salva la review di venerdì", "ingerisci le riunioni di oggi"), incolla un link teams.microsoft.com/meet o meetup-join, o vuole scegliere quali riunioni del giorno salvare.
argument-hint: "[oggi | ieri | AAAA-MM-GG | ultima | <link Teams> | <nome della riunione>]"
---

# /sb:meeting: riunioni Teams nella wiki

Argomenti: `$ARGUMENTS`

## 0. Prima di iniziare

1. Leggi `BASE/../../references/conventions.md`, dove BASE è la base directory di questa skill, ed esegui `SB version`. Fuori da una wiki: fermati e proponi `/sb:init`.
2. Servono i tool Microsoft 365 `outlook_calendar_search` e `read_resource`. Se mancano o rispondono con errore di autenticazione, dillo e fermati: non ricostruire riunioni a memoria.
3. Lavora nella radice della wiki. I file temporanei vanno in `.sb/tmp/` (già ignorata da git): creala con `mkdir -p .sb/tmp`.

## 1. Trova la riunione

Cerca **sempre** con `afterDateTime` e `beforeDateTime`: la ricerca solo testuale restituisce id che `read_resource` non sa leggere. Mostra gli orari nel fuso dell'utente, convertendo dal `timeZone` dell'evento.

| Argomento | Cosa fare |
|---|---|
| nessuno, `oggi` | Modalità lista su oggi (§2) |
| `ieri`, `AAAA-MM-GG` | Modalità lista su quel giorno (§2) |
| `ultima`, "appena finita" | Cerca da 12 ore fa ad adesso con `order: newest`. Prendi il primo evento non scartato (regole in §2) che finisce entro 15 minuti da adesso. Mostra una riga ("TouchX - Metering, 11:30–12:00, 5 persone: procedo?") e attendi conferma |
| link `teams.microsoft.com/meet/<numero>` | `query: "<numero>"`, finestra da 60 giorni fa a 60 giorni avanti |
| link `…/l/meetup-join/19%3ameeting_<token>%40thread.v2…` | `query: "<token>"` nella stessa finestra. Se non trovi nulla, leggi gli eventi della finestra con lo stesso oggetto o organizzatore e confronta `onlineMeeting.joinUrl` |
| testo libero | `query` con le parole significative, nella finestra del giorno citato (data convertita in ISO), altrimenti negli ultimi 14 giorni. Un risultato: procedi. Più risultati: una domanda a scelta multipla. Nessuno: dillo e chiedi un riferimento più preciso |

I risultati arrivano a pagine di 25: segui `nextOffset` finché serve.

## 2. Modalità lista

1. Recupera tutti gli eventi del giorno, dalle 00:00 alle 23:59 nel fuso dell'utente.
2. **Scarta**: `isCancelled`; `showAs` `oof` o `free`; `isAllDay`; eventi senza partecipanti oltre all'utente (blocchi orari, pause); eventi che l'utente ha rifiutato.
3. `SB meeting seen <id> <id> …` sugli eventi rimasti.
4. Una domanda a scelta multipla (più risposte ammesse), con un'opzione per riunione **finita e non ancora catturata**: `HH:MM–HH:MM · oggetto · N persone`. Nel testo della domanda elenca a parte le riunioni già catturate e quelle non ancora finite, che non si possono scegliere.
5. Nessuna riunione selezionabile: dillo e termina.

## 3. Recupera il materiale (per ogni riunione)

Numera le riunioni scelte da 1 a n e usa quel numero nei nomi dei file.

1. **Evento**: `read_resource` dell'`uri` dell'evento. Salva il JSON così com'è in `.sb/tmp/meeting-<n>-event.json`. Se la lettura fallisce, salta la riunione e annotalo per il riepilogo.
2. **Trascrizione**: `read_resource` di `meetingTranscriptUrl`, verbatim. Se l'evento ha `recurrence` diverso da null, aggiungi `?start=<inizio ISO>&end=<fine ISO>` dell'occorrenza.
   - Se il risultato è stato salvato su file perché troppo grande, usa quel percorso.
   - Se è arrivato inline con almeno una trascrizione non vuota, salvalo intatto in `.sb/tmp/meeting-<n>-transcript.json`.
   - Se `transcripts` è vuoto o manca `meetingTranscriptUrl`: non c'è trascrizione.
3. **Chat**: dal `joinUrl` ricava il thread decodificando la parte `19%3ameeting_…%40thread.v2` (diventa `19:meeting_…@thread.v2`). Leggi `teams:///chats/<thread>/messages`. Per ogni elemento con `messageType: message` leggi anche il suo `uri` per il testo completo e sostituisci l'elemento con la versione completa. Salva la lista di tutti gli elementi, eventi di sistema compresi, come array JSON in `.sb/tmp/meeting-<n>-chat.json`. Se la chat non si legge, prosegui senza.
4. **Senza trascrizione**: dillo e chiedi "Raccontami in due righe com'è andata, oppure scrivi 'salta'". Salva la risposta intatta in `.sb/tmp/meeting-<n>-dictation.txt`. Con "salta" la riunione è esclusa (annotalo per il riepilogo).

## 4. Cattura

    SB meeting capture --event .sb/tmp/meeting-<n>-event.json [--transcript <file>] [--chat .sb/tmp/meeting-<n>-chat.json] [--dictation .sb/tmp/meeting-<n>-dictation.txt]

- exit 0: `path` è il grezzo da analizzare.
- exit 1 con `already-captured`: la riunione era già nella wiki; saltala e riportalo.
- exit 2: leggi `error`, correggi i file se il problema è tuo, altrimenti salta la riunione e riportalo.

Poi cancella i file `.sb/tmp/meeting-<n>-*` di quella riunione. Non leggere né riscrivere la trascrizione a mano: ci pensa il toolkit.

## 5. Analisi e scrittura

Per ogni grezzo catturato esegui i **passi 3, 4 e 5** di `BASE/../put/SKILL.md` (cioè `skills/put/SKILL.md`), con il grezzo come fonte. In aggiunta:

- **Tipo**: `one-on-one` se i presenti (riga `Presenti` del grezzo; se manca, `Invitati`) sono esattamente l'utente più una persona; altrimenti `meeting`.
- **Titolo**: `AAAA-MM-GG <oggetto>` con la data della riunione, senza "Annullata:" e senza i caratteri vietati (`:` diventa ` -`). Per il one-on-one vale la sua prosa: `AAAA-MM-GG 1on1 <Nome Cognome>`.
- **`series`**: solo se l'evento è ricorrente; l'oggetto senza le parti che cambiano.
- **Persone**: `SB resolve "<Nome Cognome>"` per ogni partecipante, con le regole di ambiguità. In `attendees` metti solo chi ha già una pagina o chi la prosa del tipo `person` dice di creare; gli altri restano testo semplice. Non salvare indirizzi email.
- **Estrazione**: dalla trascrizione prendi decisioni, task nei due sensi, rischi e fatti stabili; conta ciò che è stato detto, non quanto se n'è parlato. Il parlante è il nome in `<v …>`.
- **Citazioni**: `^[raw/AAAA/MM/<slug>]`; quando aiuta, il timestamp della trascrizione nel testo, per esempio "(00:15:28)".
- **`## Note`**: non compilarla. È riservata alle valutazioni dell'utente.

## 6. Chiusura

Un solo flusso di chiusura delle convenzioni per tutte le riunioni, con `--op meeting` e messaggio `<n> riunioni · <d> decisioni · <t> task` (commit `sb(meeting): …`).

## 7. Riepilogo per l'utente

- Per ogni riunione ingerita, il riepilogo del passo 7 di `put` (creato, aggiornato, task, dubbi).
- **Saltate**: oggetto e motivo (non finita, già catturata, senza trascrizione né dettato, errore del connettore).
