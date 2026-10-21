-- ============================================================================================
-- sz_props client library (generata da fivem-sollumz). Nessuna dipendenza esterna.
-- Tutte le funzioni sono anche esportate: exports['<risorsa>']:SpawnProp(...), ecc.
-- ============================================================================================
SZ = SZ or {}

local RES = GetCurrentResourceName()

local function log(msg, ...) print(('[%s] ' .. msg):format(RES, ...)) end

--- Carica un modello in streaming. Ritorna l'hash o nil (timeout / non trovato).
function SZ.LoadModel(model, timeoutMs)
    local hash = type(model) == 'number' and model or GetHashKey(model)
    if not IsModelInCdimage(hash) or not IsModelValid(hash) then
        log('modello %s NON trovato in streaming: controlla stream/, nome file = nome archetipo, ytyp caricato', tostring(model))
        return nil
    end
    RequestModel(hash)
    local deadline = GetGameTimer() + (timeoutMs or 10000)
    while not HasModelLoaded(hash) do
        if GetGameTimer() > deadline then log('timeout caricamento %s', tostring(model)) return nil end
        Wait(0)
    end
    return hash
end

--- Spawna un prop. networked=true per farlo vedere a tutti (OneSync). Ritorna l'entity handle.
function SZ.SpawnProp(model, coords, heading, networked, freeze)
    local hash = SZ.LoadModel(model)
    if not hash then return nil end
    local obj = CreateObjectNoOffset(hash, coords.x, coords.y, coords.z, networked == true, false, false)
    SetEntityHeading(obj, heading or 0.0)
    if freeze ~= false then FreezeEntityPosition(obj, true) end
    SetModelAsNoLongerNeeded(hash)
    return obj
end

--- Carica un clip dictionary (.ycd) con timeout.
function SZ.LoadAnimDict(dict, timeoutMs)
    if HasAnimDictLoaded(dict) then return true end
    RequestAnimDict(dict)
    local deadline = GetGameTimer() + (timeoutMs or 5000)
    while not HasAnimDictLoaded(dict) do
        if GetGameTimer() > deadline then log('anim dict %s non caricato (ycd in stream? nome giusto?)', dict) return false end
        Wait(0)
    end
    return true
end

--- Riproduce un clip su un OGGETTO (prop con scheletro).
--- ATTENZIONE all'ordine: PlayEntityAnim(entity, NOME_CLIP, DIZIONARIO, ...)
--- loop: ripete ; hold: resta sull'ultimo frame (porte/coperchi aperti) ; startPhase 0.0-1.0
function SZ.PlayPropAnim(entity, dict, clip, loop, hold, startPhase, blend)
    if not DoesEntityExist(entity) then return false end
    if not SZ.LoadAnimDict(dict) then return false end
    local ok = PlayEntityAnim(entity, clip, dict, blend or 8.0, loop == true, hold ~= false, false, startPhase or 0.0, 0)
    ForceEntityAiAndAnimationUpdate(entity)
    return ok
end

function SZ.StopPropAnim(entity, dict, clip, blendOut)
    StopEntityAnim(entity, clip, dict, blendOut or 8.0)
end

function SZ.IsPropAnimPlaying(entity, dict, clip)
    -- qui l'ordine e' (entity, DIZIONARIO, CLIP, flag)
    return IsEntityPlayingAnim(entity, dict, clip, 3)
end

--- Posiziona l'animazione a un punto preciso (0.0-1.0) e la blocca li' (es. porta socchiusa)
function SZ.SetPropAnimPhase(entity, dict, clip, phase)
    if not SZ.IsPropAnimPlaying(entity, dict, clip) then SZ.PlayPropAnim(entity, dict, clip, false, true, phase) end
    SetEntityAnimCurrentTime(entity, dict, clip, phase)
    SetEntityAnimSpeed(entity, dict, clip, 0.0)
end

--- Trova il prop piu' vicino di un modello (anche quelli piazzati da ymap).
function SZ.GetClosestProp(model, coords, radius)
    return GetClosestObjectOfType(coords.x, coords.y, coords.z, radius or 3.0, GetHashKey(model), false, false, false)
end

--- Variante colore per shader *_tnt (riga della palette, 0-based).
function SZ.SetTint(entity, index)
    SetObjectTextureVariation(entity, index)
end

--- Attacca un prop alla mano destra del ped (bone 57005 = SKEL_R_Hand, 18905 = SKEL_L_Hand).
function SZ.AttachToHand(entity, ped, boneId, offset, rot)
    offset = offset or vector3(0.1, 0.02, -0.02)
    rot = rot or vector3(0.0, 0.0, 0.0)
    AttachEntityToEntity(entity, ped, GetPedBoneIndex(ped, boneId or 57005), offset.x, offset.y, offset.z,
        rot.x, rot.y, rot.z, true, true, false, true, 1, true)
end

-- --------------------------------------------------------------------------------------------
-- DUI: sostituisce una texture del modello con una pagina web (schermi, monitor, cartelloni)
-- Requisiti lato modello: la texture "placeholder" deve stare in un .ytd ESTERNO (non embedded)
-- e l'archetipo deve avere textureDictionary = quel ytd. origTxd = nome ytd, origTxn = nome texture.
-- NB: la sostituzione vale per TUTTE le istanze di quel modello (texture globale).
-- --------------------------------------------------------------------------------------------
SZ.Screens = {}

function SZ.CreateScreen(key, origTxd, origTxn, url, width, height)
    if SZ.Screens[key] then return SZ.Screens[key] end
    local rtTxdName = ('sz_rt_%s'):format(key)
    local txd = CreateRuntimeTxd(rtTxdName)
    local dui = CreateDui(url, width or 1280, height or 720)
    local deadline = GetGameTimer() + 5000
    while not IsDuiAvailable(dui) and GetGameTimer() < deadline do Wait(0) end
    local handle = GetDuiHandle(dui)
    CreateRuntimeTextureFromDuiHandle(txd, 'screen', handle)
    AddReplaceTexture(origTxd, origTxn, rtTxdName, 'screen')
    SZ.Screens[key] = { dui = dui, origTxd = origTxd, origTxn = origTxn }
    return SZ.Screens[key]
end

function SZ.ScreenSetUrl(key, url) local s = SZ.Screens[key]; if s then SetDuiUrl(s.dui, url) end end
function SZ.ScreenSend(key, tbl) local s = SZ.Screens[key]; if s then SendDuiMessage(s.dui, json.encode(tbl)) end end

function SZ.DestroyScreen(key)
    local s = SZ.Screens[key]
    if not s then return end
    RemoveReplaceTexture(s.origTxd, s.origTxn)
    DestroyDui(s.dui)
    SZ.Screens[key] = nil
end

AddEventHandler('onResourceStop', function(res)
    if res ~= RES then return end
    for key in pairs(SZ.Screens) do SZ.DestroyScreen(key) end
end)

-- --------------------------------------------------------------------------------------------
-- Porte: le porte piazzate via ymap si gestiscono col door system (lock/unlock, apertura)
-- --------------------------------------------------------------------------------------------
function SZ.RegisterDoor(uniqueName, model, coords)
    local doorHash = GetHashKey(uniqueName)
    if not IsDoorRegisteredWithSystem(doorHash) then
        AddDoorToSystem(doorHash, GetHashKey(model), coords.x, coords.y, coords.z, false, false, false)
    end
    return doorHash
end

function SZ.SetDoorLocked(doorHash, locked)
    DoorSystemSetDoorState(doorHash, locked and 1 or 0, false, true) -- 0 unlocked, 1 locked
end

-- --------------------------------------------------------------------------------------------
-- Sync multiplayer delle animazioni tramite state bag: il server (o chi possiede l'entita')
-- fa Entity(obj).state:set('szAnim', {dict=..., clip=..., loop=false, hold=true}, true)
-- e tutti i client la riproducono.
-- --------------------------------------------------------------------------------------------
AddStateBagChangeHandler('szAnim', nil, function(bagName, _, value)
    if not value then return end
    local ent = GetEntityFromStateBagName(bagName)
    local deadline = GetGameTimer() + 3000
    while (ent == 0 or not DoesEntityExist(ent)) and GetGameTimer() < deadline do
        Wait(50)
        ent = GetEntityFromStateBagName(bagName)
    end
    if ent ~= 0 then SZ.PlayPropAnim(ent, value.dict, value.clip, value.loop, value.hold) end
end)

for name, fn in pairs(SZ) do
    if type(fn) == 'function' then exports(name, fn) end
end
