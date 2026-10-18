# Design review: mappa del gioco, mappa delle schermate, run a tempi

Tre strumenti per vedere il gioco **intero** prima e dopo ogni gate, invece di guardare solo il pezzo che si sta cambiando. Valgono per ogni genere e motore. File in `docs/design-review/`, scritti dal worker `design-review` ([workers.md](workers.md)), letti dal parent, dai worker dei gate e dalla skill launch se c'è ([launch-link.md](launch-link.md) §6.2).

Lezione Buffet Panic! (ondata 9): letti tutti insieme, mappa, schermate e run hanno mostrato cose che 50 gate non avevano visto. Un negozio curato, irraggiungibile dopo il redesign del furgone. 9 tra schede e avvisi nei primi 10 s. Una spirale caduta → buffet vuoto → umore giù → richiamo che il gioco non spiegava. Camminate vuote di 8-12 s ripetute 10-15 volte. Un numero diverso tra design e codice (60 contro 50).

## Quando

| Momento | Cosa |
|---|---|
| Dopo la vertical slice (prima iterazione) | tutti e tre da zero |
| **Prima** di un gate di gameplay, UI o flusso | rinfresca quello che è più vecchio dell'ultimo gate; salva le run "prima" |
| **Dopo** il gate | rifai le run toccate con gli stessi titoli, `design_review.py runs --before`; aggiorna mappa e schermate |
| Dopo **ogni redesign** di schermate, menu, negozio, flusso o progressione | controllo orfani (§2.3) **obbligatorio** |
| Prima di un'ondata del focus group (con la skill launch) | `gate_link.py since` + i tre file aggiornati: sono lo "stato attuale" |

Con la skill launch: se in `launch/fg/waves/` ci sono `wNN-mappa-gioco.md`, `wNN-schermate.md`, `wNN-runs.md` più recenti dei tuoi, **parti da quelli** (stesso formato, [launch-link.md](launch-link.md) §9): verifica sul codice e aggiorna, non rifare da zero.

## 1. Mappa totale del gioco (`docs/design-review/game-map.md`)

Inventario letto **dal codice e dai dati**, non dal GDD. In testa: `aggiornata al gate NN (data)`.

Sezioni: giro del gioco in una riga · livelli/piani con durate e obiettivi · sistemi e regole (con i numeri) · economia (entrate, uscite, moltiplicatori) · sblocchi e meta · oggetti/perk/upgrade (tabella: effetto, prezzo, dove si ottiene, attivo nella build?) · ostacoli e nemici · eventi · HUD · comandi · accessibilità · audio · telemetria e lingue · **cosa NON c'è** · **discrepanze** (design ≠ codice, testo ≠ valore vero, es. "il testo dice 0,3 s, la base vera è 0,65 s").

- Ogni voce con il file (`percorso` o `percorso:riga`, asset, tabella dati). **[FATTO]** = letto nel codice · **[DA VERIFICARE]** = scritto nel design, non controllato.
- Le discrepanze diventano righe del piano dei gate (piccole) o domande al proprietario. Non si correggono dentro la review.

## 2. Mappa delle schermate e della scoperta (`docs/design-review/screen-map.md`)

### 2.1 Tabella
| # | Schermata (file) | Come ci arrivi (tasti / clic esatti) | Quando diventa raggiungibile | Il gioco te lo dice? | Voto |
|---|---|---|---|---|---|

Voto: **evidente** (il gioco te la mette davanti) · **trovabile** (c'è un pulsante, nessuno te lo dice) · **nascosta** (serve sapere che esiste, o non si apre mai). Mettici anche i "posti" che non sono schermate: oggetti nel mondo, negozi dentro altre schermate, funzioni sbloccabili, cosmetici, upgrade.

Come si costruisce: elenca tutte le schermate (Unity: `.uxml`, prefab UI, scene; Unreal: widget; Godot: `.tscn`), poi cerca chi le apre (eventi, `Show/Open`, `SetActive(true)`, `LoadScene`, input action, pulsanti). Una schermata che nessun codice attivo apre è un candidato orfano.

### 2.2 Blocco leggibile da macchina
````
```screens
root: Boot, MainMenu
screen: Shop | UI/Shop/Shop.uxml
screen: Roulette | UI/Roulette/Roulette.uxml | hidden-ok: spenta nella beta (D-014)
Boot -> MainMenu : auto
MainMenu -> Options : clic Options
MainMenu -> Level : clic Nuova partita
Level -> Pause : Esc
Pause -> Options : Esc > Options
Level -> LevelEnd : auto
LevelEnd -> Van : auto
Van -> Shop : pulsante Bancone
```
````
`auto` = la apre il gioco da solo (0 clic). `hidden-ok` = nascosta per scelta, con il motivo (decisione o brief).

```bash
python <SKILL>/scripts/design_review.py screens docs/design-review/screen-map.md
```
Stampa i clic dalla radice, gli **orfani**, le schermate con **un solo ingresso** (fragili a un redesign) e quelle senza uscita. Esce con 1 se c'è un orfano non dichiarato.

### 2.3 Controllo orfani dopo un redesign (obbligatorio)
Prima del gate copia la mappa in `docs/design-review/history/screen-map-gNN.md`; dopo:
```bash
python <SKILL>/scripts/design_review.py screens docs/design-review/screen-map.md --before docs/design-review/history/screen-map-gNN.md
```
- **"HANNO PERSO L'INGRESSO"** = funzioni, schermate o oggetti raggiungibili prima e non più. Ogni voce: si ricollega, oppure si ritira **apposta** (`hidden-ok` + fonte) e lo si scrive nel gate.
- **"meno ingressi"**: controlla che il giocatore la trovi ancora.
- Vale anche per gli oggetti: un upgrade venduto solo in una schermata tolta, un cosmetico senza più negozio, un perk che non esce più da nessun mazzo.

## 3. Run simulate a tempi (`docs/design-review/runs.md`)

Almeno 3 run: **giocatore nuovo** (profilo vuoto) · **giocatore che ha capito** (2ª-3ª run) · **prima vittoria o quasi**. Numeri veri dal codice, dai dati, dalla telemetria (sola lettura) e dai gate; dove dipende dal giocatore **[STIMA]**. In testa: **SIMULATO** e la build/gate.

```
## Run 1 — Giocatore nuovo
| Tempo | Dove | Azione | Numeri | A schermo |
|---|---|---|---|---|
| 0:00 | Menu | New run | — | dissolvenza 0,4 s |
| 0:12 | Livello 1 | prima scheda + obiettivo + 3 avvisi | 0/75 | [TROPPA-UI:5] [CONFUSO] |
| 0:40-0:52 | corridoio | camminata vuota col carico | — | [MORTO] |
| 1:55 | Sala | il bambino colpisce, la pila vola 6 → 1 | — | [TOP] |
| 3:10 | Sala | pila caduta → buffet vuoto → umore giù → richiamo | 34 % | [SPIRALE] [FRUSTRA] |
```
Tempo **dall'inizio della run** (mai azzerato per livello). Segni: `[MORTO]` (dura fino alla riga dopo o al range), `[TOP]` (picco, clip), `[FRUSTRA]`, `[ABBANDONO]`, `[CONFUSO]`, `[TROPPA-UI:n]` (n pannelli/avvisi insieme), `[SPIRALE]` (fallimento che alimenta fallimento senza spiegazione).

```bash
python <SKILL>/scripts/design_review.py runs docs/design-review/runs.md [--before docs/design-review/history/runs-gNN.md]
```
Tabella per run: durata, secondi morti, tratto più lungo senza un picco, massimo di UI insieme, conteggi; con `--before` le differenze (vanno nella sezione "Design review prima / dopo" del gate).

Cosa cercare: tratti morti oltre ~20 s; più di 3-4 cose a schermo insieme nei primi 10 s di un livello; spirali senza un avviso prima della punizione; momenti in cui non si capisce cosa fare; un picco divertente che arriva troppo tardi (oltre i primi 2-3 minuti).

## 4. Nel gate (prima / dopo)

- Il **piano dei gate** cita la review "prima" (data, numeri).
- Il gate ha la tabella "Design review prima / dopo" con le run toccate e la riga degli orfani ([templates/gate.md](../templates/gate.md)).
- Un gate che fa peggiorare una run (più secondi morti, più UI insieme, una spirale nuova) lo scrive in `risks`, anche se il suo obiettivo è raggiunto.
- La review è **sola lettura** sul gioco: niente fix dentro la review; le cose trovate vanno nel piano o al proprietario.
