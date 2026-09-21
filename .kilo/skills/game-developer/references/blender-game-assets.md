# Blender — Contratto "Bel Low Poly" & Modellazione Stylized

Regole di eccellenza artistica e artigianale per evitare modelli piatti o cubi grezzi ("AI-slop primitive"). Il Low-Poly professionale (stile Valheim, Gloomwood, Darkwood, Ashen) richiede silhouette, contrasto, bisellature e stratificazione.

---

## 1. La Regola Aurea: "Nessun Cubo Grezzo a Spigolo Vivo"

Un cubo primitivo a 6 facce con angoli a $90^\circ$ riflette la luce in modo piatto e sembra finto in qualsiasi motore grafico.
- **Bisellatura Obbligatoria (Chamfer / Bevel 1-Segment)**:
  Ogni trave di legno, blocco di pietra, cassa o piastra metallica deve avere bordi smussati:
  ```python
  bev = obj.modifiers.new(name="Bevel", type='BEVEL')
  bev.width = 0.025 # 2.5 cm di smusso
  bev.segments = 1  # 1 solo segmento mantiene il polycount basso ma crea il bordo che cattura la luce
  bev.limit_method = 'ANGLE'
  bev.angle_limit = 0.523599 # 30 gradi
  ```
- **Effetto specular highlight**: Nei motori come Unity URP, questo singolo segmento crea una linea di luce lungo tutti i bordi, donando profondità e peso fisico all'oggetto.

---

## 2. Stratificazione e Costruzione Reale (Layered Assembly)

Mai modellare un oggetto come una scatola monolitica con 2 cubi scalati sopra.

### Esempio: Cassa da Trasporto Medievale (Crate)
1. **Corpo interno**: Parallelepipedo base con leggera rastremazione.
2. **Telaio strutturale**: 4 montanti verticali agli angoli ($0.05\times 0.05\text{m}$) + traversi orizzontali superiori e inferiori.
3. **Doghe e assi**: Le pareti laterali non sono un poligono liscio, ma 3 assi orizzontali distinte con una microscopica fessura ($0.005\text{m}$) tra loro.
4. **Rinforzi in ferro**: Piastre angolari metalliche a "L" alle giunzioni degli spigoli.
5. **Chiodi / Borchie**: Cilindri esagonali ribassati a 6 vertici (`vertices=6`) che sporgono dalle piastre di ferro.
6. **Coperchio**: Sporgente di $0.03\text{m}$ rispetto al corpo, con una cerniera o corda laterale.

### Esempio: Barricata di Assi (Barricade)
1. **Assi irregolari**: Non clonare la stessa asse 3 volte. Variare la larghezza ($0.16\text{m}, 0.20\text{m}, 0.18\text{m}$) e lo spessore ($0.04 - 0.06\text{m}$).
2. **Tagli e scheggiature**: Le estremità delle assi non devono terminare a $90^\circ$ perfetti; inclinare o bisellare gli estremi per simulare assi segate o spaccate a colpi d'ascia.
3. **Puntone diagonale**: Un'asse trasversale a $45^\circ$ che fa da contrafforte.
4. **Rotazione imperfetta**: Ruotare ogni asse di $1^\circ - 3^\circ$ sull'asse Z. L'imperfezione crea narrazione (la barricata è stata piantata in fretta per fermare gli appestati).
5. **Borchie e chiodi forgiati**: Coppie di chiodi scuri (`#1F1F24`) su ogni punto di ancoraggio dello stipite.

---

## 3. Contrasto dei Materiali (Regola dei 3 Slot PBR)

Ogni prop deve avere almeno **2 o 3 materiali cromaticamente e matericamente contrastanti**:

| Slot | Ruolo | Colore Base (Hex) | Proprietà PBR |
|---|---|---|---|
| **Mat_Wood** | Struttura organica principale (Rovere stagionato) | `#3D2719` (o `#4A3525`) | Roughness: `0.85`, Metallic: `0.0` |
| **Mat_Iron** | Piastre, cerniere, chiodi e cerchiature | `#1E1E22` | Roughness: `0.45`, Metallic: `0.85` |
| **Mat_Accent** | Ruggine, ottone, corda o pece sigillante | `#7A5535` o `#222E21` | Roughness: `0.70`, Metallic: `0.2` |

---

## 4. Bounding Box & Geometra
1. **Pivot alla Base ($Y=0$)**: L'origine è sempre a terra per il drag-and-drop immediato.
2. **Misure Standard**:
   - Cassa standard: $0.8 \times 0.6 \times 0.5\text{m}$.
   - Baule rinforzato: $1.1 \times 0.65 \times 0.6\text{m}$.
   - Barricata per porta: $1.2\text{m}$ larghezza x altezza varco.
   - Banco alchemico: $1.8\text{m}$ lunghezza x $0.85\text{m}$ profondità x $0.80\text{m}$ altezza piano.

---

## 5. Il Protocollo Obbligatorio in 5 Passaggi per Ogni Asset

Vietato un unico `execute_blender_code`. Vietato `read_homefile` e `blender --background`. Ogni passo e una chiamata MCP + screenshot (vedi blender-mcp.md). I 5 passaggi:

1. **Passo 1: Blockout Primario & Proporzioni**:
   - Imposta i volumi generali rispettando le misure del Geometra.
   - Posiziona il pivot della base a $Y=0$.
   - Verifica la silhouette generale.

2. **Passo 2: Dettagliatura Secondaria & Bisellatura (Silhouette Breakup)**:
   - Modella i singoli componenti separati (es. montanti, assi individuali, traversi, incastri a tenone).
   - Inserisci leggere asimmetrie ed inclinazioni ($1^\circ - 3^\circ$) per dare vita al modello.
   - Applica il `Bevel Modifier` a 1 segmento su ogni elemento per creare i bordi che catturano la luce.

3. **Passo 3: Ferramenta e Accessori (Hardware & Micro-Details)**:
   - Aggiungi rinforzi in ferro battuto, staffe angolari e piastre.
   - Genera chiodi forgiati esagonali (`vertices=6`) che sporgono dalle superfici.
   - Aggiungi dettagli narrativi (es. maniglie in corda, cerniere, cunei di legno).

4. **Passo 4: Assegnazione Slot Materiali PBR a Contrasto**:
   - Applica i 3 materiali distinti (Struttura primaria, Ferramenta scura metallica, Accento ruggine/ottone).
   - Regola `Roughness` e `Metallic` per far reagire i materiali in modo differente alla luce di Unity URP.

5. **Passo 5: Ispezione Visiva, Sanitizzazione & Export**:
   - Esegui `get_viewport_screenshot` per confermare la qualità visiva del pezzo finito.
   - Applica tutte le trasformazioni (`transform_apply`).
   - Esegui la sanitizzazione ed esporta in `art/exports/<nome>.glb`.
