---
stale_operations_days: 30
one_on_one_gap_days: 21
due_soon_days: 7
---
# Layer

## knowledge

Conoscenza che cambia lentamente: chi sono le persone e come sono fatti team, progetti, sistemi e processi; quali sono i temi ricorrenti.

- Le pagine si **aggiornano e consolidano**: sezioni stabili, frasi riscritte quando i fatti cambiano, nessun diario.
- Una pagina knowledge descrive lo stato attuale. La storia si ricostruisce dalle pagine operations collegate.
- Il lint cerca contraddizioni e pagine da consolidare.

## operations

Eventi e item datati: task, 1:1, meeting, decisioni, obiettivi, rischi.

- Le pagine si **creano, si chiudono e restano**: si chiudono con `status`, non si cancellano.
- Gli eventi hanno titoli datati: `AAAA-MM-GG <descrizione>`.
- Il lint segnala i task scaduti e gli item aperti fermi da più di `stale_operations_days` giorni.

## outputs

Briefing e report generati da `/sb:prep` e `/sb:report`. Sono fotografie datate: si rigenerano nello stesso giorno, non si modificano dopo.

## Propagazione

Un'informazione operativa che cambia la conoscenza stabile aggiorna anche la pagina knowledge e la collega. Esempi:
- una decisione presa in un meeting aggiorna la pagina del progetto;
- un cambio di ruolo emerso in un 1:1 aggiorna la pagina della persona.

## Soglie

- `stale_operations_days`: giorni senza aggiornamenti dopo cui un item operativo aperto è considerato fermo.
- `one_on_one_gap_days`: giorni senza 1:1 dopo cui `/sb:status` segnala la persona (cadenza abituale + margine).
- `due_soon_days`: orizzonte di "in scadenza" per `/sb:status` e per la vista `week`.
