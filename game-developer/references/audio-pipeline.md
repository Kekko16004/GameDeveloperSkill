# Pipeline Audio Autonoma CC0 (Audio Pipeline & SFX Management)

Questa guida illustra la gestione autonoma del sound design per qualsiasi videogioco sviluppato con la skill `game-developer`. Elimina la necessità di comporre o cercare suoni manualmente, fornendo suoni autentici CC0 (Kenney Audio) e un controller audio C# pronto all'uso.

---

## 1. Architettura dell'Audio Pipeline

L'audio viene gestito attraverso 3 componenti coordinati:

1. **Libreria Suoni CC0**: Pacchetti audio royalty-free Kenney scaricati direttamente da `fetch-cc0-audio.ps1` in `art/cc0/audio/` e copiati in `Assets/_Game/Audio/`.
2. **Controller Centralizzato (`AudioManager.cs`)**: Singleton situato in `Assets/_Game/Scripts/Audio/AudioManager.cs` che gestisce i canali audio (Musica in loop, Atmosfera/Ambience, Pool SFX per effetti multipli simultanei, UI).
3. **Trigger di Gameplay**: I componenti di interazione (`IInteractable`, porte, casse, passi del player) invocano `AudioManager.Instance` con chiamate a riga singola.

---

## 2. Scaricamento Automatico con `fetch-cc0-audio.ps1`

L'agente esegue lo script PowerShell durante la fase di allestimento risorse:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.config\kilo\skills\game-developer\scripts\fetch-cc0-audio.ps1" -ProjectPath "." -Pack "all"
```

### Struttura delle Cartelle Generate nel Progetto:
```
Assets/
  _Game/
    Audio/
      SFX/         <- Passi (legno, pietra, metallo), colpi, porte, cardini, bauli
      Ambience/    <- Loop continui di vento, pioggia, atmosfera dungeon/villaggio
    Scripts/
      Audio/
        AudioManager.cs  <- Singleton di controllo
```

---

## 3. Cataloghi Audio Inclusi (Kenney CC0 Verificati)

| Pacchetto | Contenuto Principale | Utilizzo Tipico |
| :--- | :--- | :--- |
| **RPG Audio** (50 suoni) | Passi differenziati, porte cigolanti, forzieri, magia, impatti legno/metallo | Movimento player, esplorazione e interazioni ambientali |
| **Interface Sounds** (100+ suoni) | Click pulsanti, hover, confirm, cancel, popup, prompt HUD | Schermate Main Menu, Pause Menu, prompt `[E]` |
| **Impact Sounds** (70+ suoni) | Collisioni fisiche, cadute oggetti, barricamento con assi | Feedback fisico di props e combattimento |

---

## 4. Come Usare `AudioManager.cs` negli Script di Gameplay

### Setup nella Scena
1. Creare un GameObject vuoto nella scena `MainGame.unity` denominato `AudioManager`.
2. Assegnarvi lo script `AudioManager.cs`.
3. Il componente genera automaticamente i propri `AudioSource` per Musica, Ambience e un pool di 8 canali SFX indipendenti per non tagliare i suoni in sovrapposizione.

### Esempi di Chiamate nei Componenti di Gioco

#### Passi del Giocatore (`PlayerController.cs`):
```csharp
if (isMoving && stepTimer >= stepInterval)
{
    AudioManager.Instance.PlayFootstep("stone"); // oppure "wood", "dirt"
    stepTimer = 0f;
}
```

#### Apertura Porta o Baule (`DoorInteractable.cs`):
```csharp
public void OnInteract()
{
    isOpen = !isOpen;
    AudioManager.Instance.PlaySFX(openSoundClip);
}
```

#### Click Interfaccia UI Toolkit / UGUI:
```csharp
playButton.clicked += () => {
    AudioManager.Instance.PlayUI(clickSoundClip);
    StartGame();
};
```

---

## 5. Requisiti di Gate e Verifica per il Worker Audio

Il task audio è considerato `PASS` solo se rispetta queste evidenze su disco:
1. File `Assets/_Game/Scripts/Audio/AudioManager.cs` presente e compilato con 0 errori in Unity Console (`read_console`).
2. Cartella `Assets/_Game/Audio/SFX/` contenente almeno 10 file audio `.ogg` o `.wav`.
3. GameObject `AudioManager` presente nella gerarchia della scena con `AudioSource` attivi.
