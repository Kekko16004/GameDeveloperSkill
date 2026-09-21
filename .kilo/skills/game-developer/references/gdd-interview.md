# GDD Interview (Intervista a Blocchi Liberi ed Esaustivi)

**Le domande iniziali sono fondamentali: tutte le 19 vanno poste (a blocchi), nessuna saltata, e le risposte lockate in `GDD.md` decidono i tier di ogni worker successivo.** **Nessun limite rigido a una domanda per volta**: l'agente deve porre le domande raggruppate in blocchi organici e approfonditi (anche 5, 8 o 10 domande insieme se serve a definire tutto il quadro in un colpo solo), consentendo all'utente di rispondere rapidamente in uno o due passaggi anziché trascinare un lungo ping-pong. Scrivi le risposte in `GDD.md` man mano (`status: draft`). Non aprire Blender, Voxel, scene Unity o UI finché l'intervista non è completata e `status: locked`.

## Fase 1: Gameplay, Core Loop e Meccaniche (Prima il Gioco)
1. **One-Liner & Riferimenti**: Premessa del gioco in 1 frase + 2–3 titoli di riferimento nominati.
2. **Core Loop (30 Secondi)**: Qual è il ciclo di azioni ripetuto ogni 30 secondi dal giocatore?
3. **Verbi del Player**: Quali sono le azioni fisiche essenziali? (es. `move`, `jump`, `interact`, `shoot`, `dash`). Mantenere la lista corta.
4. **Condizioni di Win/Fail**: Cosa determina la vittoria e cosa la sconfitta o morte?
5. **Perimetro Vertical Slice**: 1 livello/arena, 1 tipo di nemico/ostacolo, 1 obiettivo finale chiaro.

## Fase 2: Direzione Tecnica, Stile e Motore (Poi la Forma)
6. **Motore di Gioco**: Unity 6 URP (raccomandato) oppure Godot 4.3+.
7. **Stile Grafico**:
   - `low-poly`: geometrico, texture flat, colori puliti.
   - `voxel`: cubico stilizzato, via VoxelAIArtist.
   - `cartoon`: cel-shaded, palette vibrante, forme morbide.
   - `playful`: proporzioni esagerate, colori allegri.
   - `realistic-stylized`: proporzioni realistiche con texture stilizzate.
8. **Geometria e Ambiente**: Interno (stanze/corridoi) o Esterno (arena/mappa aperta)?
9. **Telecamera**: First-Person | Third-Person (Cinemachine) | Top-Down | Isometrica.
10. **Palette e Materiale Dominante**: 4-6 colori esadecimali + 1 materiale principale (legno, pietra, metallo, plastica, neon).
11. **Architettura Completa delle Schermate UI (da creare con DesignerSkill)**:
    - **Main Menu**: Schermata iniziale con Titolo, Gioca, Opzioni (Audio/Sensibilità), Esci e sfondo atmosferico.
    - **In-Game HUD**: Parametri vitali (vita/infezione/stamina), Orologio/Fase temporale, Reticle mirino e **Prompt contestuale interattivo** (es. `[E] Apri`, `[Tasto Dx] Barrica`).
    - **Pause Menu**: Fermo gioco (`Time.timeScale = 0`), Riprendi, Riavvia livello, Menu Principale.
    - **Game Over & Vittoria**: Registro di morte o foglio di sopravvivenza con statistiche del giorno e pulsante Riprova.
    - *Inventario / Crafting*: Se previsto dal core loop, griglia slot o tavolo di distillazione.
12. **Soundscape & Paesaggio Sonoro**:
    - **Ambiente di Sottofondo**: Traccia loop atmosferica (es. vento desolato, pioggia, rintocchi lontani di campana).
    - **SFX Azioni & Verbi**: Suoni di passi diversificati (pietra/legno), cardini e porte, martellamento assi, respiro/tosse, raccolta oggetti e impatti.
    - Download automatico da pacchetti CC0 (Kenney Audio / Freesound) integrati nel mixer Unity.
  13. **Tool stack per TUTTO il gioco (obbligatoria, una sola risposta)**:
      Mostra la tabella in [tool-stack.md](tool-stack.md) e chiedi conferma o override. Vale per greybox, art, UI, audio, QA. Non rinegoziare a ogni prop.
      Default raccomandato (se l'utente dice "ok" / "consigliati"):
      - Livelli: **blueprint JSON → `GDS.LevelBuilder`** (kit modulare) + ProBuilder via `GDS.PB` (stanze/torri/scale). Mai un pezzo alla volta a mano.
      - Famiglia visiva (SCEGLIERNE UNA): Kenney | KayKit | Quaternius MegaKit Standard | Synty POLYGON Starter (solo se Q17 = sì)
      - Buco kit: Poly Pizza / Poly Haven models / Sketchfab CC0 via Blender MCP (`search` → `download` → sanitize → `export_scene`)
      - Blender: import + sanitize. Vietato modellare in Python
      - Look: `GDS.LookDev.Apply(<preset Q19>)` + palette GDD; toon/outline opzionali
      - Personaggi: KayKit / Kenney animati / Quaternius UAL → `GDS.Characters`
      - UI: real-world-design → UI Toolkit (OBBLIGATORIO, mai UXML a mano)
      - Audio: Kenney CC0 + AudioManager
      - QA: `GDS.SceneLint` (issues 0) + Play Mode + TerminalMCP WASD
      - Client Blender: `uvx blender-mcp` stdio, porta 9876 TCP — mai `http://localhost:9876/mcp`
      Override ammessi solo se nominati (es. "tutto voxel", "ho Kenney All-in-1 in D:\Kenney").
      Vietato come piano: Sloyd Guest, Blockbench, Dust3D, cubi bpy, mix di due famiglie, muri piazzati uno a uno via `manage_gameobject`.

  14. **Modalità Sessione / Cambio Chat Forzato**:
      Chiedi se attivare il blocco forzato della chat o procedere in continuo:
      - `continuous` (**Raccomandato per Claude Code e Kilo Code** con subagents): nessun blocco forzato; i subagents gestiscono i task isolati e il parent prosegue senza interruzioni manuali. Il contesto vive su disco (`GAME_CONTEXT.md`, `art/blueprints/*.json`, `art/kit-catalog.json`, `docs/lint/*.json`), non nella chat.
      - `hard-stop` (**Raccomandato per Antigravity** e client monochat senza subagents): arresto forzato con banner `[HARD STOP]` e ripresa via `/resumegame` dopo ogni macrotask per non saturare la chat.

  15. **Strategia Modelli 3D: Chi realizza gli asset di gioco? (Obbligatoria)**:
      Chiedi se i modelli 3D devono essere creati dall'agente o forniti dall'utente:
      - `agent-full` (**Default automatico**): L'agente ricerca, compone e sanitizza tutti i modelli (Kit Kenney/KayKit/Quaternius + Poly Pizza CC0 + Blender MCP).
      - `user-provided` (**Modelli forniti dall'utente**): L'utente modella o importa i propri asset 3D. L'agente genera subito il manifesto `art/ASSET_MANIFEST.md` con l'elenco esatto degli asset, i nomi file (`prop_xxx.glb` o `.fbx`), la cartella di destinazione (`art/exports/`), le dimensioni indicative in metri e il vincolo di pivot a terra ($Y=0$). Quando l'utente inserisce i file e lancia `/resumegame` dicendo *"Ho messo i modelli"*, l'agente verifica la loro presenza, valida il formato e li collega automaticamente alla scena/prefabs.
      - `hybrid` (**Ibrido**): L'utente fornisce gli asset "Hero" o chiave (personaggio, edificio principale, reliquia), mentre l'agente genera i modelli secondari di contorno (casse, pavimentazione, clutter).

## Fase 3: Hardware, budget e look (obbligatorie — decidono i tier per tutta la pipeline)

  16. **Generazione 3D (hero prop) — tier e budget (Obbligatoria)** → `GDD.md: gen3d:`
      Spiega in 3 righe: kit + Poly Pizza coprono il 90 %; il generativo serve solo per 3–5 prop unici. Opzioni ([gen3d.md](gen3d.md)):
      - `none` (**default**): solo CC0. Consigliato se non c'è key né GPU.
      - `local`: Modly (Hunyuan3D-2mini / TripoSG / TRELLIS2) offline, **NVIDIA ≥ 8 GB VRAM** (6 GB = solo shape, lento). Chiedi la GPU (Q18) prima di proporlo.
      - `meshy` | `tripo`: key API (`MESHY_API_KEY` / `TRIPO_API_KEY` nell'env del MCP CoplayDev → `generate_model`). Chiedi **budget crediti** (`gen3dBudgetCredits`) e **max asset** (`gen3dMaxAssets`, default 5). Il worker si ferma al cap e riporta i crediti usati nel gate.
      - `hyper3d`: key trial/free nel pannello Blender MCP (Rodin).
      Se l'utente dice "ho la key Meshy, spendi poco": `gen3d: meshy`, `gen3dBudgetCredits: 200`, `gen3dMaxAssets: 3`, prompt template `low poly stylized game asset, flat colors, single object, no base`.

  17. **Asset Store gratuiti (Obbligatoria)** → `GDD.md: assetStore: yes|no`
      Synty POLYGON Starter Pack, Cartoon FX Remaster Free, Unity Particle Pack: gratis, EULA standard (commerciale OK), **non CC0**, serve account Unity e download da Package Manager (browser TerminalMCP se serve). `yes` sblocca Synty come famiglia e CFX come VFX. `no` = solo CC0 puro.

  18. **Hardware (Obbligatoria)** → `GDD.md: gpu:`, `vram:`
      GPU e VRAM dell'utente (es. "GTX 1660 Super 6 GB"). Decide: `gen3d: local` ammesso (≥ 8 GB), qualità lookdev (`ssao` off sotto 4 GB), risoluzione HDRI (1k/2k), light baking sì/no.

  19. **Look preset (Obbligatoria)** → `GDD.md: lookdev:`
      Una delle ricette in [lookdev.md](lookdev.md): `stylized-day` | `stylized-sunset` | `dungeon-torch` | `night-moon` | `pastel-bright` | `scifi-cold`, + opzionali `toon: yes|no`, `outline: yes|no`, `hdri: <nome Poly Haven | none>`. Se l'utente non sa: proponi in base a Q7/Q8 (interno dungeon → `dungeon-torch`; esterno cartoon → `stylized-day`).

## Blocco e Transizione (Lock)
Dopo la risposta 19 (tool stack, session mode, asset strategy, gen3d + budget, asset store, hardware, look preset locked):
- Mostra il riepilogo: **Dichiarato** vs **Inferito**.
- Se l'utente sceglie `user-provided` o `hybrid`, mostra in anteprima la bozza dell'elenco asset con cartella di destinazione.
- Se l'utente corregge: aggiorna e rimostra.
- Quando approvato: imposta `status: locked` in `GDD.md`.
- Solo adesso passa alla fase di creazione/scaffold del progetto.
