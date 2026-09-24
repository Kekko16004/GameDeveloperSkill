# GameDeveloperSkill

Pipeline autonoma da idea a vertical slice Unity beta-ready: intervista GDD, poi un worker isolato per fase. Edifici veri da generatore Blender procedurale, livelli da blueprint (kit CC0 o ProBuilder), lint di scena deterministico, lookdev, personaggi, VFX, UI.

Il villaggio e un ambiente tra gli altri: caverna, dungeon, interno, citta, sci-fi e natura aperta hanno il loro flusso (`game-developer/references/environments.md`).

## Avvio

```bat
check-status.bat       :: verifica stato
start-dashboard.bat    :: console: progetto, FabCLI, DesignerSkill
install.bat            :: installa la skill sugli host (Kilo, Claude, Codex, Antigravity)
```

La console (`game-developer/tools/tui/gds_tui.py`) non e un sito: tre schermate, `1` `2` `3` per cambiare, `e` modifica un percorso, `s` salva, `q` esce. Serve Python 3.10+, nessun pacchetto.

## Struttura

```
game-developer/            la skill (SKILL.md + tutto il resto)
  references/              un file per fase, letti on demand
  scripts/                 fetch kit CC0, doctor, installer GDS, generatore edifici
  templates/               C# GDS (Editor), generatore Blender, blueprint di esempio
  command/                 /game, /gdd, /playtest, /resumegame
  tools/tui/               la console
  config.json              percorsi e moduli (locale, gitignorato nei deploy)
scripts/                   check dipendenze e stato
docs/                      audit e storico
```

`install.ps1` copia la skill negli host. Le copie deployate (`.kilo/`, `.claude/`, ...) non stanno nel repo.

## Configurazione

Tutto sta in `game-developer/config.json` (parti da `config.example.json`):

| Chiave | A cosa serve |
|---|---|
| `paths.voxelai` / `paths.designerSkill` / `paths.terminalmcp` | tool esterni |
| `paths.blender` / `paths.unityCli` / `paths.godot` | eseguibili |
| `fab.enabled`, `fab.cli`, `fab.library_path` | FabCLI (libreria Fab/MegaScan personale) |
| `modules.*` | accende/spegne i pezzi |
| `art.gen3dDefault` | `none` di default: zero costi |

## Workflow

1. `/game` — intervista GDD (19 domande, incluso il tipo di mondo).
2. La pipeline lancia un worker per fase: greybox, kit, edifici, livelli, mondo, lookdev, personaggi, sistemi, UI, juice, playtest.
3. Ogni fase chiude con un gate su disco (`docs/gates/`) e `lint: issues 0`. Nessun "fatto" senza file.

## Asset

- Kit CC0 per genere: Kenney, KayKit, Quaternius (`references/cc0-sources.md`, `scripts/fetch-cc0-kits.ps1`).
- Hero prop: Poly Pizza, poi Poly Haven, poi Sketchfab CC0, poi il tier gen3d scelto nel GDD.
- FabCLI solo per la libreria Fab personale, e solo se `fab.enabled` e true.

## Documentazione

- `INSTALL.md` — installazione
- `docs/AUDIT-2026-09.md` — perche la pipeline e fatta cosi
- `docs/archive/` — report delle versioni precedenti
- `docs/ideas/` — idee non implementate (bozze, non funzionalita)
