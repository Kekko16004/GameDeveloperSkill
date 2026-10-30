-- GDS playtest telemetry (GameDeveloperSkill, quality-baseline.md "Playtest kit", references/nucleon/tests.md §6c).
-- OPT-IN: records only when the player said yes (SaveData("telemetry", {optIn = true}), e.g. from a first-run prompt or
-- the options menu) or when the environment variable NC_GDS_TELEMETRY=1 is set (tester builds). Nothing leaves the PC:
-- one CSV per session in Saved/telemetry/<date>_<time>_<level>.csv that the tester sends back by hand.
-- Columns: t (seconds of play), event, level, x, y, z (the pawn, Z up), value, extra.
-- Automatic: session_start, level, pos (every `every` seconds: heatmap and time per area), idle (no movement for 20 s),
-- quit. From the game: exports.gds_telemetry:Log("death", {cause = "spikes"}) or TriggerEvent("gds:telemetry", "pickup", 1).
-- Read by scripts/telemetry_report.py (deaths per area, where players stop, time to the first objective, quit points).
local saved = LoadData("telemetry") or {}
local env = os.getenv("NC_GDS_TELEMETRY")
local enabled = saved.optIn == true or (env ~= nil and env ~= "" and env ~= "0")
exports("Enabled", function() return enabled end)
exports("SetOptIn", function(yes)
  saved.optIn = yes and true or false
  SaveData("telemetry", saved)
  enabled = saved.optIn or (env ~= nil and env ~= "" and env ~= "0")
end)

local file, startTime = nil, nil
local every = tonumber(os.getenv("NC_GDS_TELEMETRY_EVERY") or "") or 2

local function csv(v)
  v = tostring(v == nil and "" or v)
  if v:find('[,"\n]') then v = '"' .. v:gsub('"', '""') .. '"' end
  return v
end

local function open()
  if file or not enabled then return file end
  os.execute(package.config:sub(1, 1) == "\\" and 'mkdir "Saved\\telemetry" 2>nul' or "mkdir -p Saved/telemetry")
  local level = (GetCurrentLevel and GetCurrentLevel() or "level"):gsub("[^%w]+", "_")
  file = io.open(("Saved/telemetry/%s_%s.csv"):format(os.date("%Y%m%d_%H%M%S"), level), "w")
  if file then
    file:write("t,event,level,x,y,z,value,extra\n")
    startTime = GetGameTime()
  end
  return file
end

local function log(event, value, extra)
  if not open() then return end
  local p = GetLocalPlayer() and GetPlayerPawn(GetLocalPlayer())
  local pos = p and DoesEntityExist(p) and GetEntityPosition(p) or vec3(0, 0, 0)
  local ex = ""
  if type(extra) == "table" then
    local parts = {}
    for k, v in pairs(extra) do parts[#parts + 1] = k .. "=" .. tostring(v) end
    table.sort(parts)
    ex = table.concat(parts, ";")
  elseif extra ~= nil then ex = tostring(extra) end
  if type(value) == "table" and extra == nil then
    local parts = {}
    for k, v in pairs(value) do parts[#parts + 1] = k .. "=" .. tostring(v) end
    table.sort(parts)
    ex, value = table.concat(parts, ";"), ""
  end
  file:write(("%.2f,%s,%s,%.2f,%.2f,%.2f,%s,%s\n"):format(GetGameTime() - startTime, csv(event),
    csv(GetCurrentLevel and GetCurrentLevel() or ""), pos.x, pos.y, pos.z, csv(value), csv(ex)))
  file:flush()
end
exports("Log", log)
AddEventHandler("gds:telemetry", function(event, value, extra) log(event, value, extra) end)

if not enabled then return end

CreateThread(function()
  Wait(0)
  log("session_start", os.date("%Y-%m-%d %H:%M:%S"))
  log("level", GetCurrentLevel and GetCurrentLevel() or "")
  local last, still = nil, 0
  while true do
    Wait(math.floor(every * 1000))
    local p = GetLocalPlayer() and GetPlayerPawn(GetLocalPlayer())
    if p and DoesEntityExist(p) then
      local pos = GetEntityPosition(p)
      log("pos")
      if last and Distance(pos, last) < 0.3 then
        still = still + every
        if still >= 20 and still - every < 20 then log("idle", still) end
      else
        still = 0
      end
      last = pos
    end
  end
end)
AddEventHandler("onLevelLoaded", function(path) log("level", path or "") end)
AddEventHandler("onQuit", function() log("quit") if file then file:close() file = nil end end)
