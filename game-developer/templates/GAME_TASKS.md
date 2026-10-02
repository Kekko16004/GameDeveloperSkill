# GAME_TASKS — Registro Task

> **Regola:** un task = un deliverable verificabile (un blueprint, un mondo, un batch di hero prop, un verbo con script + test + hook, una schermata UI). Target 60-80 task, max 90 ([task-decomposition.md](../references/task-decomposition.md)). Vietati task macro ("fai il villaggio") e task per click ("piazza muro 17", "istanzia prefab a (0,0,15)": le posizioni stanno nei JSON di blueprint/world/village). Un task è `[x]` solo con evidenza su disco (JSON di build/lint, GLB > 15KB, PNG, test verde, console 0 errori).

## Stato Globale
- **Totale:** 0 · **Fatti:** 0 (0%) · **In corso:** 0 · **Bloccati:** 0
- **Ultimo checkpoint:** nessuno (regressione + commit ogni 10 task `[x]`, vedi task-decomposition.md)
- **Tempo totale:** 0 min

## Legenda
- `[ ]` da fare · `[/]` worker attivo · `[x]` fatto con evidenza · `[!]` bloccato dopo 2 retry (motivo in Note; i task che non dipendono da lui vanno avanti)
- **Dipende:** ID dei task che devono essere `[x]` prima (vuoto = libero). Un `[!]` blocca solo chi lo cita qui.
- **Inizio:** `HH:MM` quando passa a `[/]`. **Durata:** minuti quando chiude (`[x]` o `[!]`), retry inclusi.

| ID | Fase | Descrizione (tutti i numeri che servono al worker) | Spec / File | Evidenza | Dipende | Stato | Inizio | Durata | Note |
|---|---|---|---|---|---|---|---|---|---|
| TASK-001 | SETUP | Attach/create progetto Unity 6 URP, install GDS editor, `gds_ping`, git init + .gitignore Unity | `ProjectSettings/`, `Assets/_Game/Editor/GDS/` | `docs/gates/04-project.md` PASS | | [ ] | | | |
| TASK-002 | SETUP | Input actions (Move, Look, Interact E, Pause Esc) + tag/layer + scene `MainMenu` (index 0) e `MainGame` (index 1) | `Assets/_Game/Settings/`, `Assets/_Game/Scenes/` | console 0 | 001 | [ ] | | | |
| TASK-010 | GREY | Greybox da `art/blueprints/PLAN.md` (`mode: probuilder`), ground top Y=0, controller del genere + `PlayerMovementTests` | `art/blueprints/*.json`, `Scripts/Player/*` | test verde + lint 0 + `screenshots/010-greybox-play.png` | 002 | [ ] | | | |
| TASK-020 | KIT | Fetch famiglia kenney (medieval), catalogo, scala metrica, recolor palette GDD | `art/kit-catalog.json` | `docs/gates/07-kit-fetch.md` | 001 | [ ] | | | |
| TASK-021 | WORLD | Overworld terrain 400 m, seed 42, flat villaggio (0,0,35), scatter pini/querce/rocce dal catalogo | `art/world/overworld.json` | world JSON PASS + lint 0 + sheet | 010, 020 | [ ] | | | |
| TASK-030 | BP | BP-house_a — 3x2 celle, 1 piano, porta S1, finestra N0, tetto kit, interno tavolo + 2 sedie + baule, origin (0,0,12) | `art/blueprints/house_a.json` | build JSON + lint 0 + PNG | 020 | [ ] | | | |
| TASK-040 | HERO | Batch hero: relic, altar, signpost (Poly Pizza → Poly Haven → Sketchfab CC0) | `art/exports/*.glb` | `blender-*.png` + GLB > 15 KB | 020 | [ ] | | | |
| TASK-050 | LOOK | Palette + `gds_lookdev stylized-day` + torce VFX | `Assets/_Game/Settings/LookDev_*.asset` | PNG con fog/bloom/ombre + lint 0 | 021, 030 | [ ] | | | |
| TASK-051 | REVIEW | Art review #1 (`gds_sheet`, rubric R1-R7) | `docs/gates/art-review-1.md` | media ≥ 4, nessun voto < 3 | 050 | [ ] | | | |
| TASK-060 | SYS | Interact: `IInteractable` + `DoorInteractable` (slerp) + raycast nel controller + prompt HUD `[E] Apri` + test `Interact_OpensDoor` | `Scripts/Interaction/*` | test verde + console 0 | 010 | [ ] | | | |
| TASK-070 | UI | Main Menu — real-world-design, 3-4 varianti, scelta utente, UI Toolkit | `ui/main-menu/`, `Assets/_Game/UI/MainMenu.*` | mock HTML + PNG Play Mode | 050 | [ ] | | | |
| TASK-090 | QA | Playtest completo (menu → obiettivo → win/fail) | `docs/gates/playtest.md` | PNG Play Mode con HUD + tutti i test verdi | tutti | [ ] | | | |
| TASK-091 | SLICE | Recap gate e report slice | `docs/gates/slice.md` | tutti i gate PASS | 090 | [ ] | | | |
