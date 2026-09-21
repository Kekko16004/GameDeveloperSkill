# GDD Interview (Intervista a Blocchi Liberi ed Esaustivi)

**Nessun limite rigido a una domanda per volta**: l'agente deve porre le domande raggruppate in blocchi organici e approfonditi (anche 5, 8 o 10 domande insieme se serve a definire tutto il quadro in un colpo solo), consentendo all'utente di rispondere rapidamente in uno o due passaggi anziché trascinare un lungo ping-pong. Scrivi le risposte in `GDD.md` man mano (`status: draft`). Non aprire Blender, Voxel, scene Unity o UI finché l'intervista non è completata e `status: locked`.

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
13. **Strategia Asset 3D & Rapporto di Produzione (Online CC0 vs Fatto da Zero)**:
    Chiedi sempre all'utente come vuole bilanciare la produzione visiva:
    - **A. Ibrido Coerente (Raccomandato)**: Scarica kit CC0 online con **stile visivo omogeneo** per le strutture modulari d'ambiente (case, strade, vegetazione, arredi base) + modella con Blender MCP / VoxelAI tutti gli oggetti chiave e unici di gameplay.
    - **B. Modellazione su Misura (80% - 100% da zero)**: L'agente modella gli asset da zero con Blender MCP (protocollo Bel Low Poly in 5 passaggi) o VoxelAI per un'estetica artigianale al 100% esclusiva.
    - **C. Kit Online Prioritari**: Sfrutta al massimo pack CC0 gratuiti per assemblare l'intero livello rapidamente a costo zero.
    *Vincolo di Coerenza*: Qualsiasi asset scaricato deve appartenere alla stessa famiglia stilistica (stesso livello di low-poly, palette armonizzata, stesso shader) per evitare collage visivi disordinati.

## Blocco e Transizione (Lock)
Dopo la risposta 13:
- Mostra il riepilogo: **Dichiarato** vs **Inferito**.
- Se l'utente corregge: aggiorna e rimostra.
- Quando approvato: imposta `status: locked` in `GDD.md`.
- Solo adesso passa alla fase di creazione/scaffold del progetto.
