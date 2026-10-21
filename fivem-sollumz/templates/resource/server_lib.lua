-- ============================================================================================
-- sz_props server helpers (OneSync). Spawn di prop networked + animazioni sincronizzate.
-- ============================================================================================
SZS = SZS or {}

--- Crea un prop networked lato server (visibile a tutti). Ritorna l'entity handle server.
function SZS.SpawnNetworkedProp(model, coords, heading)
    local obj = CreateObjectNoOffset(GetHashKey(model), coords.x, coords.y, coords.z, true, true, false)
    local deadline = GetGameTimer() + 3000
    while not DoesEntityExist(obj) and GetGameTimer() < deadline do Wait(0) end
    if not DoesEntityExist(obj) then return nil end
    SetEntityHeading(obj, heading or 0.0)
    FreezeEntityPosition(obj, true)
    return obj
end

--- Fa partire un clip su tutti i client (vedi handler 'szAnim' in client_lib.lua).
function SZS.PlayPropAnimForAll(obj, dict, clip, loop, hold)
    Entity(obj).state:set('szAnim', { dict = dict, clip = clip, loop = loop == true, hold = hold ~= false,
        t = os.time() }, true)
end

for name, fn in pairs(SZS) do
    if type(fn) == 'function' then exports(name, fn) end
end
