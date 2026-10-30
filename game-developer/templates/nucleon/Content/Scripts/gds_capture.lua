-- GDS capture for store pages and trailers (GameDeveloperSkill, `ncli.py capture plan.json`, references/nucleon/tests.md §6b).
-- Runs only when Saved/gds-capture.lua exists (ncli writes it from the plan JSON, deletes it after Stop).
-- Rules-safe by design (playtest.md "Catture fedeli alle regole"): it moves the camera, presses keys like a player and
-- hides UI documents; it never touches timers, score, spawns or the game state. Every shot is labelled real-play.
-- Shot fields: name, at (seconds of play), camera ("player" | {position, lookAt, fov} | {follow = "pawn", offset}),
-- hide (UI documents to hide, e.g. {"UI/hud.rml"}), press (key held for `hold` s before the shot), frames + interval
-- (a GIF sequence), wait (extra seconds after the camera move). One log line per file:
--   GDS-CAPTURE shot <name> <file> ok|failed      ...      GDS-CAPTURE DONE shots=<n> failed=<m>
local f = io.open("Saved/gds-capture.lua", "rb")
if not f then return end
local chunk = load(f:read("a"), "gds-capture", "t", {})
f:close()
if not chunk then print("GDS-CAPTURE DONE shots=0 failed=1 error=parse") return end
local plan = chunk()
local out = plan.out or "captures"

local function frameTime() local dt = GetFrameTime() return dt > 0 and dt or 1 / 30 end
local function waitSeconds(s) local e = 0 while e < s do Wait(0) e = e + frameTime() end end
local function v(t) return vec3(t[1], t[2], t[3]) end
local function pawn() return GetPlayerPawn(GetLocalPlayer()) end

local function setCamera(cam)
  if cam == nil or cam == "player" then ResetCamera() return end
  if cam.follow then
    local target = cam.follow == "pawn" and pawn() or GetEntityByName(cam.follow)
    if target then AttachCameraToEntity(target, cam.offset and v(cam.offset) or nil) end
  else
    if cam.position then SetCameraPosition(v(cam.position)) end
    if cam.lookAt then SetCameraLookAt(v(cam.lookAt)) end
  end
  if cam.fov then SetCameraFov(cam.fov) end
end

local seq = 0
local function shoot(file)
  Wait(0) Wait(0) Wait(0)   -- let the frame with the new camera be drawn
  if not plan.viaEditor then return TakeScreenshot(file) end   -- packaged / standalone: the game window
  -- Play In Editor: TakeScreenshot would grab the whole editor window, so ncli captures the game viewport (MCP
  -- capture_viewport) when it reads the "ready" line, and answers by creating Saved/gds-capture-ack-<n>
  seq = seq + 1
  print(("GDS-CAPTURE ready %d %s"):format(seq, file))
  local ack, waited = ("Saved/gds-capture-ack-%d"):format(seq), 0
  while waited < 30 do
    local h = io.open(ack, "rb")
    if h then
      local ok = h:read("a") == "ok"
      h:close()
      os.remove(ack)
      return ok
    end
    Wait(0)
    waited = waited + frameTime()
  end
  return false
end

CreateThread(function()
  local start = GetGameTime()
  local ok_n, fail_n = 0, 0
  table.sort(plan.shots, function(a, b) return (a.at or 0) < (b.at or 0) end)
  for _, s in ipairs(plan.shots) do
    while GetGameTime() - start < (s.at or 0) do Wait(0) end
    if s.press then
      SimulateKey(s.press, true)
      waitSeconds(s.hold or 0.15)
      SimulateKey(s.press, false)
    end
    for _, doc in ipairs(s.hide or {}) do   -- a document the game never showed is not an error of the capture
      if not pcall(HideUI, doc) then print(("GDS-CAPTURE note %s: %s is not loaded"):format(s.name, doc)) end
    end
    local camOk, camErr = pcall(setCamera, s.camera)
    if not camOk then print(("GDS-CAPTURE note %s: camera %s"):format(s.name, tostring(camErr))) end
    if s.wait then waitSeconds(s.wait) end
    local n = s.frames or 1
    for k = 1, n do
      local file = n > 1 and ("%s/%s_%03d.png"):format(out, s.name, k) or ("%s/%s.png"):format(out, s.name)
      local ok = shoot(file)
      if ok then ok_n = ok_n + 1 else fail_n = fail_n + 1 end
      print(("GDS-CAPTURE shot %s %s %s"):format(s.name, file, ok and "ok" or "failed"))
      if k < n then waitSeconds(s.interval or 0.08) end
    end
    for _, doc in ipairs(s.hide or {}) do pcall(ShowUI, doc) end
    if s.camera and s.camera ~= "player" then pcall(ResetCamera) end
  end
  print(("GDS-CAPTURE DONE shots=%d failed=%d"):format(ok_n, fail_n))
end)
