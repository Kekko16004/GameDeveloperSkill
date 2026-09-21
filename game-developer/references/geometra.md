# Il Geometra — Contratto Dimensionale e Regole di Snap

Il Geometra governa tutte le dimensioni, scale e posizionamenti di stanze, modelli modulari, arredi e personaggi nel gioco.

## 1. Unità Fondamentale
- **1 ProBuilder/Kenney/KayKit/Blender Unit = 1 Unity Unit = 1 Metro**.
- Nessuna scala arbitraria. Kit: un import scale per cartella. Handmade: Apply All Transforms prima dell'export.

## 2. Griglia e Snap Modulare
Tutti i componenti ambientali devono allinearsi alla griglia standard:
- **Modulo Pavimento**: $4.0 \times 4.0\text{ m}$, spessore $0.2\text{ m}$.
- **Modulo Parete**: $4.0\text{ m}$ (larghezza) $\times 3.0\text{ m}$ (altezza) $\times 0.2\text{ m}$ (spessore).
- **Modulo Angolo**: $0.2 \times 0.2\text{ m}$ alla giunzione, altezza $3.0\text{ m}$.
- **Modulo Porta**: Vano $1.0\text{ m}$ (larghezza) $\times 2.2\text{ m}$ (altezza) ricavato all'interno della parete da $4.0\text{ m}$.
- **Corridoi**: Larghezza minima $2.0\text{ m}$ per consentire rotazione camera e navigazione fluida.

## 3. Ergonomia e Player Scale
- **Altezza Player**: $1.8\text{ m}$, raggio cilindro $0.4\text{ m}$.
- **Altezza Occhi (Camera First-Person)**: $1.6\text{ m}$.
- **Altezza Gradino Massima (senza salto)**: $0.3\text{ m}$.
- **Altezza Salto Tipica**: $1.2\text{ m}$.

## 4. Arredi e Oggetti (Misure Reali)
- **Tavolo**: Altezza piano $0.75\text{ m}$, $1.6 \times 0.8\text{ m}$.
- **Sedia**: Altezza seduta $0.45\text{ m}$, schienale $0.9\text{ m}$.
- **Bancone / Desk**: Altezza $1.0\text{ m}$.
- **Scaffale / Libreria**: Altezza $2.0\text{ m}$, profondità $0.4\text{ m}$.
- **Letto Singolo**: $2.0 \times 1.0\text{ m}$, altezza $0.5\text{ m}$.

## 5. Regola Assoluta dei Pivot (Punti di Origine)
- **Pavimenti e Muri**: Pivot all'angolo inferiore sinistro a quota $Y=0$ (Min X, Min Z, Min Y). Questo permette lo snap istantaneo su Unity con vertice $[0,0,0]$.
- **Arredi, Oggetti e Prop**: Pivot al centro della base d'appoggio a quota $Y=0$ (X=Center, Z=Center, Min Y=0).
- **Personaggi / Nemici**: Pivot a terra tra i due piedi ($X=0, Z=0, Y=0$).

## 6. Verifica Geometra
Le stanze nascono in ProBuilder su questa griglia. I kit Kenney/KayKit si snappano agli stessi moduli. Prima di importare:
1. Verificare che il bounding box rispetti i valori di `config/metrics.json`.
2. Verificare che l'origine sia a $Y=0$.
3. Verificare che le facce abbiano normali orientate verso l'esterno.
