# Characters & animation — CC0, no Mixamo dependency

Mixamo is unmaintained since 2025 (auto-rigger often down). Use CC0 packs that already ship a humanoid rig + clips.

| Need | Source | License | Notes |
|---|---|---|---|
| Stylized player/enemies **with animations** | KayKit Adventurers / Skeletons (`fetch-cc0-kits.ps1 -Genre characters`) | CC0 | glTF + FBX, ~20 clips each, matches KayKit kits |
| Blocky / prototype chars with animations | Kenney Animated Characters (Protagonists / Survivors / Retro), Kenney Prototype Kit | CC0 | FBX/glTF, 8–27 clips |
| Any humanoid + big clip library | Quaternius **Universal Base Characters** (6 bodies, 20 hairstyles) + **Universal Animation Library** Standard (45 clips: locomotion, combat, emotes) | CC0 | Humanoid rig, retargets in Unity; itch "name your price" → $0 |
| Realistic-ish | Poly Haven models (no rig) — avoid for characters | CC0 | props only |
| Missing hero character | Poly Pizza (Blender MCP) rigged search, then UAL retarget | CC0/CC-BY | check `animations` flag in result |

## Unity setup (worker `characters`)

1. Copy chosen FBX/GLB to `Assets/_Game/Art/Characters/<pack>/`. Copy UAL clips to `Assets/_Game/Art/Characters/UAL/` if using a rig without clips.
2. `return GDS.Characters.SetHumanoidFolder("Assets/_Game/Art/Characters/<pack>");` → Humanoid rig, loop on all clips except death.
3. `return GDS.Characters.ListClips();` → pick names.
4. `return GDS.Characters.BuildController("Player", "Idle", "Walk", "Run", "Jump", "Attack", "Hit", "Death");` → `Assets/_Game/Animation/Player.controller` (Speed blend tree + triggers). Missing clip names come back in `missingClips`; pick another or omit.
5. `return GDS.Characters.MakePrefab("Knight.fbx", "Assets/_Game/Animation/Player.controller", "char_player");` → prefab with Animator + CharacterController sized from bounds.
6. Wire `PlayerController` (template) → `animator.SetFloat("Speed", velocity.magnitude)`, `SetTrigger("Jump")`.
7. Enemies: same controller pattern (`char_enemy_*`) + NavMesh: run skill **`initialize-ai-navigation`** (installed) → NavMeshSurface bake, `NavMeshAgent` on enemies, one `EnemyChase.cs` (set destination = player if distance < aggro).
8. Scale check: player bounds height 1.6–2.0 m (Geometra). If not, fix `SetImportScale` on the pack folder, not the prefab.
9. Screenshot Play Mode `screenshots/050-characters.png` with the character walking (Speed > 0). Gate `docs/gates/09-characters.md` with the JSON returns.

Rules: Humanoid, not Generic, for anything that will use UAL/Mixamo clips. Root motion off (CharacterController drives). One character family per slice (KayKit chars with KayKit kits; Kenney with Kenney; UBC with any low-poly).
