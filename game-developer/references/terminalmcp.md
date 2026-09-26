# TerminalMCP — Controllo Totale di Sistema

Repository: https://github.com/Fonlogen/TerminalMCP (Node 18+, zero-dipendenze).
Percorso installazione: `paths.terminalmcp` in `config.json` (rilevato dall'installer in `%USERPROFILE%\Desktop\Dev Things\TerminalMCP`, `%USERPROFILE%\Desktop\TerminalMCP` o `%USERPROFILE%\Documents\TerminalMCP`).
Profilo attivo: `--tools all` (29 tool completi: shell, job, vars, search, git, fs, archive, sys, net, dev, data, watch, browser, screen, input).

## Capacità Operative Principali
L'agente ha pieno controllo dell'ambiente locale tramite i seguenti comandi:

1. **Gestione Processi & Applicazioni**:
   - Avvio/chiusura di Blender, Unity Hub, o qualsiasi software ausiliario tramite `shell_exec` o `shell_exec_async`.
   - Controllo dello stato tramite `proc` e `shell_job`.

2. **Interazione GUI & Finestre (Occhi e Mani)**:
   - Identificazione e focus finestra: `screen { action: "shot", mode: "window", window: "Unity" }`.
   - Superamento di popup o dialog modali bloccanti dell'Editor Unity: click tramite `input { action: "click", x, y, window: "...", shot: true }`.

3. **Simulazione Input nel Play Mode (QA Bot)**:
   - Iniezione reale di tasti WASD, Spazio (salto), E (interazione):
     `input { action: "key", keys: "w", hold_ms: 1200, window: "Unity", shot: true }`.
   - Verifica immediata della risposta fisica del personaggio tramite screenshot catturato direttamente sul Game View.

4. **Ispezione Visiva & Screenshotting**:
   - Lettura di qualsiasi immagine o frame su disco: `screen { action: "view", path: "<game>/screenshots/001-playmode.png" }`.
   - Copia automatica di tutti i frame catturati nella cartella `<game-project>/screenshots/` con aggiornamento dell'indice `000-index.md`.

5. **Watcher Compilazione e Log Live**:
   - Monitoraggio in tempo reale dei log di Unity o dei build watcher con `watch { action: "start" }` per correggere al volo errori di compilazione CS.
