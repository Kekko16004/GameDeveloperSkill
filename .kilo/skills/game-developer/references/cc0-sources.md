# Risorse CC0 Gratuite Online — Asset 3D e Audio Universali

L'acquisizione di asset CC0 gratuiti è applicabile a **qualsiasi genere e ambientazione** (Medievale, Sci-Fi, Western, Post-Apocalittico, Cartoon, Voxel). 

L'obiettivo è duplice:
1. Rispettare il rapporto di produzione scelto dall'utente nell'intervista (es. 100% CC0, 50/50 Ibrido, oppure 80% fatto da zero a mano).
2. **Garantire la coerenza stilistica assoluta**: vietato creare "Frankenstein visivi" con modelli realistici affiancati a modelli cartoon.

---

## 1. Catalogo Universale per Ambientazione (Tutti CC0)

| Genere / Stile | Fonti e Pacchetti Raccomandati | Formati & Note |
|---|---|---|
| **Medieval / Fantasy** | KayKit Medieval & Dungeon (`github.com/KayKit-Game-Assets`), Kenney Castle & Fantasy | GLTF/FBX. Legno, pietra, tegole, armature, armi |
| **Sci-Fi / Cyberpunk / Space** | Kenney Space Kit, Kenney Retro Urban, Poly Haven Sci-Fi Props | GLTF/FBX. Moduli corridoio, console, tubature, casse metalliche |
| **Western / Deserto** | Kenney Western Kit, Poly Haven Desert/Cactus | GLTF/FBX. Edifici in legno a facciata, saloon, botti, staccionate |
| **Modern / Post-Apocalittico** | Kenney City Kit, Kenney Survivor/Post-Apoc | GLTF/FBX. Strade asfaltate, veicoli abbandonati, detriti, container |
| **Cartoon / Low-Poly Pulito** | Kenney Prototype & Urban Kit, KayKit Mini City | Flat shaded, colori saturi, forme amichevoli |
| **Voxel Puro** | VoxelAIArtist (`mcp_server`) + librerie MagicaVoxel CC0 | Modelli a cubi voxel con palette indicizzata |

---

## 2. Il Filtro di Coerenza Stilistica (Anti-Frankenstein)

Quando si scaricano asset online, l'agente deve applicare 3 controlli di coerenza prima dell'import definitivo in Unity:

1. **Densità Poligonale Compatibile**: Non mischiare prop ad altissimo polycount (es. 50k triangoli) con elementi low-poly da 200 triangoli.
2. **Armonizzazione dei Materiali & Palette**: Tutti i modelli devono condividere lo stesso shader in Unity (es. URP Lit o URP Simple Lit) e palette coerenti con il `GDD.md`. Se necessario, riassegnare il materiale comune della scena (`Mat_Wood`, `Mat_Stone`, `Mat_Metal`).
3. **Scala Uniforme del Geometra**: Verificare che 1 unità corrisponda sempre a 1 metro (porte a $2.2\text{m}$, pareti a $3\text{m}$, casse da $0.6-0.8\text{m}$).

---

## 3. Soundscape Universale (Audio CC0)

Per qualsiasi ambientazione, il gioco deve possedere:
- **Traccia Loop d'Atmosfera**:
  - Sci-Fi: Ronzio generatori, aria condizionata della stazione spaziale.
  - Medieval/Horror: Vento sordo, pioggia, campana.
  - Western: Ululato del vento, polvere, cicale.
- **Set SFX Verbi**:
  - Passi specifici per superficie (metallo, pietra, legno, terra).
  - Suoni di interazione (porte, leve, terminali, raccolta oggetti).
  - Feedback d'impatto o allarme.
- **Fonti**: Kenney Audio (`RPGAudio`, `ImpactSounds`, `SciFiAudio`, `InterfaceSounds`), Freesound CC0.
