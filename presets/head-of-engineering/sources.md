---
sources: {}
---
# Sorgenti esterne

Registro delle knowledge base esterne. Una sorgente esterna è **autorevole sui fatti** che documenta. La wiki ne conserva una sintesi (`source-note`) e propaga i fatti nelle pagine tipizzate, sempre con citazione.

Ogni sorgente è una riga nel frontmatter:

    sources:
      conf-eng: {system: confluence, scope: ENG, covers: [process, system], stale_after_days: 30}
      jira-plat: {system: jira, scope: PLAT, covers: [project], stale_after_days: 14}

- `system`: `confluence`, `jira` o un altro sistema raggiungibile via MCP.
- `scope`: chiave dello spazio o del progetto (`ENG` in `confluence:ENG/123`, `PLAT` in `jira:PLAT-42`).
- `covers`: tipi di pagina che vivono soprattutto in questa sorgente.
- `stale_after_days`: dopo quanti giorni una source-note va ricontrollata con `/sb:sync`.

Link web (`url:`) e mail (`mail:`) non si registrano: sono catture una tantum.

Sotto, una sezione per ogni sorgente: a cosa serve, chi la mantiene, cosa ingerire e cosa no.
