---
gate: NN
title: <titolo breve, quello che il proprietario riconosce>
date: YYYY-MM-DD
status: PASS
source: [launch/fg/waves/wNN-sintesi.md, docs/gates/plan-wNN.md]
wave: wNN
closes: [<chiave-issue_status>]
verify: [<chiave-da-confermare-con-persone-vere>]
todo: ["<parole che trovano UNA riga aperta di launch/TODO.md>"]
decisions: [D-NNN]
files:
  - Assets/_Game/Scripts/<file>.cs
screenshots:
  - docs/screens/NN/01-<cosa>-after.png
risks:
  - "<rischio di gameplay introdotto: cosa può peggiorare, per chi, come si vede>"
owner_try:
  - "<azione concreta da provare, 1 riga>"
design_changes:
  - "nessuno: implementato come nel brief"
saves: backup + restore identical
build: none
tests: not run (il proprietario prova da sé, D-NNN)
---
# Gate NN: <titolo> (YYYY-MM-DD)

<!-- Contratto: launch-link.md §7. Validare con: python <SKILL>/scripts/gate_link.py --project <PROJECT> check docs/gates/NN-<slug>.md
     Regole dell'intestazione:
     - closes = chiavi chiuse da questo gate (solo con status PASS) -> issue_status "risolto"; verify -> "da_verificare".
       Mai chiavi che sono decisioni del proprietario (accettato / non_problema / pianificato / sospeso).
     - nessun valore vuoto: dove non c'è niente scrivi "nessuno: <motivo>" (o none: <reason>).
     - design_changes: ogni scelta di design diversa dal brief, "cosa | perché | decided_by: implementer"
       oppure "decided_by: owner (<fonte: brief AAAA-MM-GG / chat AAAA-MM-GG / D-NNN>)". Mai "owner" senza fonte.
     - screenshots guardati uno per uno (non solo salvati); mai in Temp/ o Library/.
     - build: none salvo richiesta esplicita del proprietario. tests: niente suite se DECISIONI dice che prova lui. -->

Motore e versione. Fonte: <ondata / note del proprietario / piano>.
- **Controlli:** compilazione 0 errori; lint scena / controllo testi / sim di feel con i numeri veri.
- **Salvataggi:** backup prima del primo Play (<dove>), salvataggi del Play in una cartella temporanea, ripristino verificato ("identici", con hash).
- **Prove:** dove e come (scena vera, gioco normale, strumenti di debug che passano dalle regole del gioco).

## Design review prima / dopo
| Run (design-review/runs.md) | Morti | Max senza picco | UI insieme | Spirale |
|---|---|---|---|---|
| <run> | prima → dopo | | | |

Orfani (`design_review.py screens --before`): nessuno / <elenco con la correzione>.

## 1. <punto del brief>
- **Cosa non andava:** <misurato prima, con numeri>.
- **Causa:** <la causa vera, non il sintomo>.
- **Fix:** <cosa è cambiato>.
- **Verificato nel gioco normale:** <la meccanica vera, da tutte le direzioni/situazioni in cui il giocatore la incontra: davanti, di lato, da dietro; numeri prima → dopo>.
- **Foto:** prima `...-before.png`, dopo `...-after.png`.

## Rischi di gameplay introdotti
- <cosa può peggiorare per il giocatore, e chi deve ricontrollarlo nella prossima ondata o coi tester veri>

## Scelte di design cambiate
- <stessa lista di design_changes, in parole semplici; "nessuna" se nessuna>

## File
- **Nuovi:** ...
- **Modificati:** ...

## Dubbi rimasti
- ...

## Per il proprietario
<Lingua del proprietario, parole semplici, niente nomi di file se non servono.>
**Fatto:** 1. ... 2. ...
**Da provare tu:**
1. <come owner_try>
