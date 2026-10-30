-- GDS playthrough bot for Nucleon (GameDeveloperSkill, `ncli.py playthrough`, references/playtest.md "Playthrough").
-- INERT unless NC_GDS_PLAYTHROUGH is set in the environment or ncli wrote Saved/gds-playthrough.lua (it does, for the verb).
-- It plays the game like a player would, with real input events (SimulateKey / SimulateMouseButton / SimulateMouseMove): it
-- reads the input map of the game (GetInputActions + GetActionBindings), presses EVERY bound input of every action, looks around,
-- and logs one line per step with what it saw (pawn and camera moved, pause opened, a watched value changed), the frame time of
-- the step and a screenshot. A step it cannot drive (a wheel, a gamepad, an unknown key) is logged `undrivable` with the reason,
-- never skipped silently: the parent reads those and reports them as `engine_gap:`.
-- Extra steps from the plan (the verbs of this game): {name, input = "Key.R", seconds = 0.2, watch = "GetAmmo()", expect = "after < before"}.
-- Lines:  GDS-PLAY {"n":1,"action":"Jump","input":"Key.Space","status":"driven","observed":"...","p95_ms":..,"shot":".."}
--         GDS-PLAY DONE driven=<n> undrivable=<n> failed=<n>      (a packaged run exits 0 / 3 with NC_GDS_TEST_EXIT=1)
-- Natives are Z up.
local planFile = io.open("Saved/gds-playthrough.lua", "rb")
local enabled = planFile ~= nil or (os.getenv("NC_GDS_PLAYTHROUGH") or "") ~= ""
if not enabled then if planFile then planFile:close() end return end
local plan = {}
if planFile then
  local chunk = load(planFile:read("a"), "gds-playthrough", "t", {})
  planFile:close()
  plan = chunk and chunk() or {}
end
local out = plan.out or "screenshots/playthrough"
local hold = plan.hold or 0.7
local CX, CY = 640, 360

local function now() return Async and Async.now and Async.now() or os.clock() end
local function frameTime() local dt = GetFrameTime() return dt > 0 and dt or 1 / 30 end
local function wait(s) local e = 0 while e < s do Wait(0) e = e + frameTime() end end
local function esc(s) return (tostring(s):gsub('[%c"\\]', function(c) return c == '"' and "'" or " " end)) end
local function pawn() local p = GetLocalPlayer() return p and GetPlayerPawn(p) end

local seq = 0
local function shoot(file)
  Wait(0) Wait(0) Wait(0)
  if not plan.viaEditor then return TakeScreenshot(file) end
  seq = seq + 1
  print(("GDS-CAPTURE ready %d %s"):format(seq, file))      -- ncli captures the game viewport and answers with an ack file
  local ack, waited = ("Saved/gds-capture-ack-%d"):format(seq), 0
  while waited < 30 do
    local h = io.open(ack, "rb")
    if h then local ok = h:read("a") == "ok" h:close() os.remove(ack) return ok end
    Wait(0) waited = waited + frameTime()
  end
  return false
end

local function state()
  local p, s = pawn(), {}
  if p and DoesEntityExist(p) then s.pos = GetEntityPosition(p) end
  if GetCameraPosition then s.cam = GetCameraPosition() end
  s.paused = (IsGamePaused and IsGamePaused()) or (IsPauseMenuOpen and IsPauseMenuOpen()) or false
  return s
end
local function dist(a, b) return a and b and Distance(a, b) or 0 end

-- "Key.LeftShift" -> {kind="key", name="Left Shift"}; Mouse.Left -> button 1; Mouse.Delta -> look; the rest cannot be injected
local BUTTON = {Left = 1, Middle = 2, Right = 3}
local function classify(input)
  local kind, name = input:match("^(%a+)%.(.+)$")
  if kind == "Key" then return "key", (name:gsub("(%l)(%u)", "%1 %2")), name end
  if kind == "Mouse" then
    if BUTTON[name] then return "button", BUTTON[name] end
    if name:find("Wheel") or name:find("Scroll") then return "none", "no native injects the mouse wheel (SimulateMouseWheel missing)" end
    return "look", name
  end
  if kind == "Pad" then return "none", "no native injects a gamepad input" end
  return "none", "unknown input kind " .. input
end

local function press(kind, a, b, down)
  if kind == "key" then
    local ok = SimulateKey(a, down)
    if not ok and b and b ~= a then ok = SimulateKey(b, down) end
    return ok
  elseif kind == "button" then return SimulateMouseButton(CX, CY, a, down)
  elseif kind == "look" then if down then return SimulateMouseMove(CX, CY, 40, 0) end return true end
end

local function run(n, step)
  local kind, a, b = classify(step.input)
  local rec = {n = n, action = step.action, input = step.input}
  if kind == "none" then
    rec.status, rec.observed = "undrivable", a
    return rec
  end
  local before = state()
  local watchBefore
  if step.watch then local f = load("return " .. step.watch) watchBefore = f and select(2, pcall(f)) end
  local t0, times, last = now(), {}, now()
  if not press(kind, a, b, true) then
    rec.status, rec.observed = "undrivable", ("SimulateKey/Mouse refused the input name %q"):format(tostring(a))
    return rec
  end
  local seconds, e, shotFile = step.seconds or hold, 0, nil
  while e < seconds do
    Wait(0)
    local n2 = now()
    times[#times + 1] = (n2 - last) * 1000
    last = n2
    e = e + frameTime()
    if not shotFile and e >= seconds * 0.5 then
      shotFile = ("%s/step-%02d-%s.png"):format(out, n, ((step.action or "x"):gsub("%W", "_")))
      rec.shot = shoot(shotFile) and shotFile or nil
    end
  end
  press(kind, a, b, false)
  wait(0.3)
  local after = state()
  table.sort(times)
  rec.p95_ms = tonumber(("%.1f"):format(times[math.max(1, math.ceil(#times * 0.95))] or 0))
  local seen = {}
  if dist(before.pos, after.pos) > 0.2 then seen[#seen + 1] = ("pawn moved %.1f m"):format(dist(before.pos, after.pos)) end
  if dist(before.cam, after.cam) > 0.05 and dist(before.pos, after.pos) <= 0.2 then seen[#seen + 1] = ("camera moved %.2f m"):format(dist(before.cam, after.cam)) end
  if before.paused ~= after.paused then
    seen[#seen + 1] = after.paused and "game paused" or "game resumed"
    if after.paused then   -- close it, or every later step plays into a menu; saying whether it closed is part of the test
      if ClosePauseMenu then pcall(ClosePauseMenu) end
      if SetGamePaused then pcall(SetGamePaused, false) end
      Wait(0) Wait(0)
      seen[#seen + 1] = state().paused and "PAUSE DID NOT CLOSE" or "pause closed"
    end
  end
  if step.watch then
    local f = load("return " .. step.watch)
    local ok, v = pcall(f)
    seen[#seen + 1] = ("%s: %s -> %s"):format(step.watch, tostring(watchBefore), tostring(v))
    if step.expect then
      local g = load("local before, after = ...; return " .. step.expect)
      local okE, res = pcall(g, watchBefore, v)
      if not (okE and res) then rec.status = "failed" seen[#seen + 1] = "expect failed: " .. step.expect end
    end
  end
  rec.status = rec.status or "driven"
  rec.observed = #seen > 0 and table.concat(seen, "; ") or "no visible change: read the screenshot"
  return rec
end

local function json(r)
  local parts = {}
  for _, k in ipairs({"n", "action", "input", "status", "observed", "p95_ms", "shot"}) do
    local v = r[k]
    if v ~= nil then parts[#parts + 1] = ('"%s":%s'):format(k, type(v) == "number" and tostring(v) or ('"' .. esc(v) .. '"')) end
  end
  return "{" .. table.concat(parts, ",") .. "}"
end

CreateThread(function()
  local waited = 0
  while not (GetLocalPlayer() and pawn() and DoesEntityExist(pawn())) do
    Wait(0) waited = waited + frameTime()
    if waited > 20 then print("GDS-PLAY DONE driven=0 undrivable=0 failed=1 error=no-pawn") return end
  end
  wait(plan.settle or 1.5)
  local steps = {}
  for _, act in ipairs(GetInputActions()) do
    for _, b in ipairs(GetActionBindings(act.name) or {}) do steps[#steps + 1] = {action = act.name, input = b.input} end
  end
  steps[#steps + 1] = {action = "Look", input = "Mouse.Delta", seconds = 0.6}
  for _, s in ipairs(plan.extra or {}) do steps[#steps + 1] = {action = s.name, input = s.input, seconds = s.seconds, watch = s.watch, expect = s.expect} end
  local driven, undrivable, failed = 0, 0, 0
  for i, step in ipairs(steps) do
    local ok, rec = pcall(run, i, step)
    if not ok then rec = {n = i, action = step.action, input = step.input, status = "failed", observed = tostring(rec)} end
    print("GDS-PLAY " .. json(rec))
    if rec.status == "driven" then driven = driven + 1 elseif rec.status == "undrivable" then undrivable = undrivable + 1 else failed = failed + 1 end
    for _, k in ipairs({"W", "A", "S", "D", "Space", "Left Shift", "Left Ctrl", "E", "R"}) do SimulateKey(k, false) end
  end
  print(("GDS-PLAY DONE driven=%d undrivable=%d failed=%d"):format(driven, undrivable, failed))
  io.stdout:flush()
  if os.getenv("NC_GDS_TEST_EXIT") == "1" then os.exit(failed == 0 and 0 or 3) end
end)
