# Manuale Universale di Modellazione 3D e Gestione Asset per Videogiochi (Architecture, Props & User Protocol)

Questo manuale è la guida tecnica e artistica definitiva della skill `game-developer` per istruire qualsiasi intelligenza artificiale (Kilo Code, Claude, Codex, Antigravity) o sviluppatore umano nella creazione, composizione e integrazione di asset 3D commerciali per Unity, Godot o Unreal Engine.

---

## 0. Regola Zero Obbligatoria: Reset e Pulizia Preventiva della Scena (Zero-Pollution)

> [!CAUTION]
> **MAI IMPORTARE O MODELLARE SU UNA SCENA SPORCA**
> L'errore più grave e frequente di un'agente AI su Blender è dimenticarsi di ripulire la scena prima di inserire un nuovo modello. Se la scena contiene ancora oggetti da un task precedente (es. il pozzo precedente o le luci di default), il nuovo asset verrà importato sopra il vecchio e durante l'export finale verranno fusi insieme creando un "modello mostro" ingiocabile.

Prima di qualsiasi ricerca, download Poly Pizza o esecuzione di script, **esegui sempre come primo passo il blocco di wipe totale**:

```python
import bpy

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for mesh in list(bpy.data.meshes):
    bpy.data.meshes.remove(mesh, do_unlink=True)
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat, do_unlink=True)
```

---

## 1. I 4 Pilastri Fondamentali del 3D Game Asset

Indipendentemente dal genere (Medievale, Sci-Fi, Cyberpunk, Low-Poly, Realistico), ogni asset 3D deve rispettare rigorosamente questi 4 principi per evitare artefatti visivi, difetti di scala o il tipico aspetto sciatto ("scatola grigia / AI slop"):

### 1. La Scala Metrica Assoluta (1 Unità = 1 Metro)
Nei motori moderni, l'illuminazione fisica (URP Lit, Lumen) e la fisica dei corpi rigidi (PhysX) dipendono dalla dimensione reale:
- **Altezza piano edificio**: $2.60\text{m} - 3.20\text{m}$.
- **Porte**: larghezza $0.90\text{m} - 1.20\text{m}$, altezza $2.10\text{m} - 2.40\text{m}$.
- **Tavoli e banchi di lavoro**: altezza $0.75\text{m} - 0.90\text{m}$.
- **Sedute / Sedie**: altezza seduta $0.45\text{m} - 0.50\text{m}$.
- **Casse e barili**: $0.40\text{m} - 0.70\text{m}$.
- **Personaggi umani**: altezza $1.70\text{m} - 1.85\text{m}$.

### 2. La Legge del Pivot a Terra ($Z=0$, Centro $X=0, Y=0$)
Un asset il cui pivot risiede al centro del bounding box sprofonda nel pavimento quando viene istanziato su una superficie tramite Raycast o griglia ProBuilder.
- Il vertice più basso della mesh deve avere quota $Z=0.0000$.
- Il centro della base d'appoggio deve trovarsi esattamente a $X=0.0000, Y=0.0000$.
- Tutte le rotazioni e scale devono essere congelate prima dell'export (`transform_apply`).

### 3. Bisellatura a 1 Segmento (Chamfer Anti-Slop)
Gli spigoli a $90^\circ$ matematicamente perfetti non esistono nel mondo reale e nelle luci dei motori grafici appaiono piatti e finti. Un bevel minimale a 1 solo segmento (`width = 0.01 - 0.02m`, `limit_method = 'ANGLE'`) cattura la luce speculare, delinea la silhouette dell'oggetto e mantiene il polycount bassissimo.

### 4. Contrasto PBR e Canali Emissivi
Un modello di qualità commerciale non usa mai un unico materiale piatto. Deve presentare forte contrasto tra:
- **Superfici opache ad alta rugosità** (Roughness 0.85–0.95, Metallic 0.0): pietra, legno grezzo, intonaco, cemento, terreno.
- **Superfici levigate / metalliche** (Roughness 0.25–0.45, Metallic 0.85–0.95): ferro battuto, ottone, acciaio, oro, cromo.
- **Canale Emissivo Vivo** (Emission Strength 4.0–10.0): finestre illuminate dall'interno, fiamme, braci di forgiatura, pozioni chimiche, display sci-fi, rune magiche.

---

## 2. Flusso 1: Modellazione Architettonica da Concept / Reference 2D

Quando si deve creare un edificio a partire da un'immagine o disegno, è tassativamente vietato estrudere un blocco unico. L'architettura va decomposta in **strati modulari sovrapposti**.

### La Formula dei Livelli Sovrapposti (Esempio Reale: Casa Medievale Fantasy)

```
                                [ Comignolo Colmo ]
                                        │
                         [ Abbaino Grande Timpanato ]
                                        │
                        ┌───────────────────────────────┐
                        │    Tetto Principale Falde     │
                        │      (Pendenza 45°, Tegole)   │
                        └───────────────┬───────────────┘
                                        │
    [ Abbaino Secondario ]    [ Fasce Graticcio/Pannelli]     [ Torretta Sporgente ]
    [ con Tubo Stufa     ]    [ Montanti a Raggiera     ]     [ Sbalzo su Puntone  ]
           │                                │                         │
    ┌──────┴───────────┐      ┌─────────────┴───────────┐     ┌───────┴────────┐
    │ Tetto a Falda SX │      │ Galleria Balconata      │     │ Tetto a FaldaDX│
    └──────┬───────────┘      │ (Pilastri + Parapetto)  │     └───────┴────────┘
           │                                │                         │
    ┌──────┴───────────┐      ┌─────────────┴───────────┐     ┌───────┴────────┐
    │ Basamento Ovest  │      │ Corpo Centrale Massiccio│     │ Basamento Est  │
    │ Apertura Second. │      │ Portale + Bugnato Angolo│     │ Finestra Vano  │
    └──────────────────┴──────┴─────────────────────────┴─────┴────────────────┘
    ─────────────────────────────────────────────────────────────────────────── (Quota Terra Z = 0)
```

1. **Basamento di Fondazione**: Volumi cubici primari per corpo centrale e ali laterali. Aggiunta di blocchi d'angolo sporgenti a scaletta (*quoins*) con materiale a contrasto scuro.
2. **Aperture Inferiori**: Telai incassati, portali ogivali o squadrati con battenti colorati e accessori in ferro.
3. **Marcapiano e Sbalzo (Jettying)**: Trave o cornice orizzontale in legno o metallo che sporge rispetto al piano inferiore.
4. **Galleria / Balcone**: Mensole inclinate di supporto (*corbel brackets*), pianale di camminamento e parapetto a montanti verticali e correnti orizzontali.
5. **Orditura di Facciata**: Struttura a graticcio (puntoni diagonali a raggiera a $0^\circ, \pm 32^\circ, \pm 45^\circ$) per spezzare l'uniformità dell'intonaco.
6. **Copertura Principale e Abbaini**: Falde del tetto inclinate a $45^\circ$ con colmo cilindrico e abbaini timpanati incassati nelle falde.
7. **Canne Fumarie**: Comignoli differenziati (tubo stufa con cappuccio conico, camino in muratura squadrata, gomito metallico).
8. **Illuminazione Interna**: Vetri dotati di materiale autoilluminante caldo dorato (`Mat_EmissiveWindow`, Emission `#FFDD66`, strength 8.0).

---

## 3. Flusso 2: Hybrid Assembly (Kit-Bashing Avanzato con Poly Pizza)

Per oggetti densamente decorati (officine, carretti carichi, altari mistici), la composizione rapida tramite mesh modulari CC0 scaricate da Poly Pizza offre resa tripla rispetto alla modellazione manuale isolata.

### La Formula dell'Unparenting con Matrice Intatta
I modelli importati da Poly Pizza sono vincolati a un `RootNode` con scale e orientamenti arbitrari. Se si stacca l'oggetto con `obj.parent = None` senza congelare la matrice, la mesh si deforma o sparisce. Eseguire sempre:

```python
import bpy

def unparent_keep_transform(obj):
    mat = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = mat
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.select_set(False)

for o in list(bpy.data.objects):
    if o.type == 'EMPTY':
        bpy.data.objects.remove(o, do_unlink=True)
```

### Catalogo Asset CC0 Indispensabili (Testati e Verificati)

| Categoria | Oggetto | ID Poly Pizza | Autore | Licenza | Utilizzo Tipico |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Trasporti** | Cart | `l7bDe7ak6j` | Quaternius | CC0 1.0 | Carri merci, banchi mercato ambulanti |
| **Stoccaggio** | Barrel | `MraIiFnpAY` | Quaternius | CC0 1.0 | Barili rustici, birra, polvere da sparo |
| **Stoccaggio** | Crate | `3VGWnZPXmG` | Quaternius | CC0 1.0 | Casse di legno con rinforzi a X |
| **Luce** | Hanging Lantern | `3jzk3YShv1` | Kay Lousberg | CC0 1.0 | Lanterne da appendere con gancio |
| **Officina** | Workbench Anvil | `bY1pp3kAAb` | Kenney | CC0 1.0 | Incudine su ceppo con martello |
| **Officina** | Workbench Grind | `hnxYRW4Nx3` | Kenney | CC0 1.0 | Mola ad acqua e pietra da affilare |
| **Armi** | Knight Sword | `9lLmH8Et4K` | Quaternius | CC0 1.0 | Spade, reliquie, trofei |
| **Ambiente** | Rock Large | `54jZKTAt5p` | Quaternius | CC0 1.0 | Rocce monolitiche, altari |
| **Strutture** | Forge Workshop | `2ZnLsJJL4Pe` | Don Carson | CC-BY 3.0 | Officina fabbro completa con travi e scudi |

---

## 4. Protocollo di Collaborazione: Modelli Agente vs Modelli Utente

Nella skill generale, la domanda obbligatoria 15 in fase di GDD (`gdd-interview.md`) definisce la strategia degli asset:
- `agent-full`: L'agente genera o assembla autonomamente tutti i modelli.
- `user-provided`: L'utente fornisce i propri modelli 3D.
- `hybrid`: L'utente fornisce i modelli chiave/hero, l'agente genera i secondari.

### Quando l'Utente Fornisce i Modelli: Il Manifesto (`art/ASSET_MANIFEST.md`)
Se viene selezionata l'opzione `user-provided` o `hybrid`, l'agente **NON deve rimanere bloccato** e non deve pretendere i file immediatamente. Genera subito il documento `art/ASSET_MANIFEST.md`:

```markdown
# ASSET_MANIFEST.md — Elenco Modelli 3D Richiesti

### Istruzioni per l'Utente / Artista 3D
1. Posiziona i tuoi modelli esportati nella cartella: `art/exports/`
2. Formato richiesto: `.glb` (raccomandato per PBR) oppure `.fbx`.
3. Scala: 1 unità = 1 metro reale.
4. Pivot: quota Min Z = 0 (base a terra, non centrato nel volume).
5. Quando hai posizionato i file, lancia il comando `/resumegame` oppure scrivi in chat: *"Ho messo i modelli"*. L'agente verificherà la presenza su disco, testerà la metrica e li collegherà alla scena Unity.

| ID Asset | Nome File Obbligatorio | Cartella Destinazione | Dimensioni Indicative (X, Y, Z) | Ruolo nel Gioco | Stato |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `well` | `prop_plague_well.glb` | `art/exports/` | $1.20 \times 1.20 \times 1.50\text{m}$ | Pozzo infetto interagibile | `[ ] In attesa` |
| `house` | `building_house.glb` | `art/exports/` | $6.00 \times 4.00 \times 7.00\text{m}$ | Edificio rifugio giocatore | `[ ] In attesa` |
| `chest` | `prop_chest.glb` | `art/exports/` | $1.00 \times 0.60 \times 0.80\text{m}$ | Baule loot | `[ ] In attesa` |
```

### Ripresa Trasparente con `/resumegame`
Quando l'utente inserisce i modelli e richiama `/resumegame`:
1. L'agente scansiona la cartella: `Test-Path "art/exports/<nome_asset>.glb"`.
2. Verifica che il peso sia valido ($> 5\text{KB}$) e non un file corrotto o vuoto.
3. Se presente, aggiorna `ASSET_MANIFEST.md` a `[x] Pronto` e `GAME_TASKS.md` a `[x]`.
4. Importa direttamente il modello in Unity, configura il prefab e lo posiziona alle coordinate previste nel task successivo.

---

## 5. Modelli Verificati ed Esportati nel Repository

Tutti i seguenti modelli sono pronti all'uso e salvati sia in `game-developer/art/exports/` che in `SkillMadeGame/art/exports/`:

| File GLB | Poligoni | Dimensioni (X, Y, Z) | Dettagli Architetturali e Materiali |
| :--- | :--- | :--- | :--- |
| **building_medieval_fantasy_house.glb** | 1.201 | $6.34\times 3.21\times 7.43\text{m}$ | Casa a 2 piani + mansarda con graticcio Tudor, balconata su mensole, tetto verde a scaglie, abbaino timpanato, bovindo laterale e 3 comignoli |
| **prop_blacksmith_forge_deluxe.glb** | 19.339 | $2.50\times 1.86\times 1.31\text{m}$ | Officina fabbro completa con travi a vista, banco da lavoro, incudine, scudi, attrezzi e focolare con braci vive emissive |
| **prop_merchant_wagon.glb** | 6.093 | $1.00\times 2.00\times 1.72\text{m}$ | Carretto mercantile con ruote a 10 raggi, tendalino a strisce, barile cerchiato, casse impilate e lanterna appesa autoilluminante |
| **prop_runic_shrine_sword.glb** | 1.211 | $1.60\times 1.53\times 1.37\text{m}$ | Monolite di granito con spada d'acciaio e oro conficcata a $7^\circ$, sigillo ottagonale, candele con cera fusa e cristalli di mana azzurro |
| **prop_medieval_war_chest.glb** | 418 | $1.10\times 0.65\times 0.85\text{m}$ | Baule rinforzato con coperchio semicilindrico a botte, fascioni verticali in ferro, borchie esagonali e lucchetto |
| **prop_magic_alchemy_table.glb** | 512 | $1.60\times 0.90\times 1.25\text{m}$ | Tavolo a doghe con grimorio, fiala di pozione verde inclinata a mezz'aria e 2 anelli toroidali orbitali |

---

## 6. Script Universale di Sanitizzazione e Pivot Snap

Ogni script di esportazione DEVE concludersi con questo blocco per garantire un'integrazione perfetta nel motore di gioco:

```python
import bpy, mathutils

bpy.ops.object.select_all(action='DESELECT')
mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
for obj in mesh_objs:
    obj.select_set(True)

bpy.context.view_layer.objects.active = mesh_objs[0]
bpy.ops.object.join()

final_obj = bpy.context.active_object
final_obj.name = "nome_asset_finale"

for obj in list(bpy.data.objects):
    if obj != final_obj:
        bpy.data.objects.remove(obj, do_unlink=True)

bbox = [mathutils.Vector(corner) for corner in final_obj.bound_box]
min_z = min(v.z for v in bbox)
center_x = (min(v.x for v in bbox) + max(v.x for v in bbox)) / 2.0
center_y = (min(v.y for v in bbox) + max(v.y for v in bbox)) / 2.0

offset = mathutils.Vector((-center_x, -center_y, -min_z))
for v in final_obj.data.vertices:
    v.co += offset
final_obj.data.update()

final_obj.location = (0, 0, 0)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
```
