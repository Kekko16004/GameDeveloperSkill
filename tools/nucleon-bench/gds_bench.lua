-- GDS performance bench for Nucleon (GameDeveloperSkill tools/nucleon-bench). bench.py copies this file into
-- Content/Scripts/ for the run and removes it after. It runs only when Saved/gds-bench.lua exists (the plan bench.py writes).
--
-- For every scenario of the plan it drives the camera itself (no player input), records one CSV row per frame and marks the
-- window in the log ("GDS-BENCH begin <name>" / "GDS-BENCH end <name>") so bench.py can take the NC_GPU_PROFILE lines of that
-- window. Frame time = Async.now() between frames (a steady clock: GetFrameTime is capped at 0.1 s and scaled by time).
-- Scenarios:
--   view      {name, kind = "view", position = {x,y,z}, lookAt = {x,y,z}, seconds}            steady cost of one view
--   fly       {name, kind = "fly", points = {{pos, look}, ...}, speed (m/s)}                   traversal: streaming, LOD changes
--   approach  {name, kind = "approach", target = "<entity name>" | {x,y,z}, from = 60, to = 2,  walking up to an asset: the
--              height = 1.7, seconds = 8, dir = {x,y}, repeat = 2}                              close-up drops (pages, mips)
-- Settings applied before the scenarios (one config of the matrix): plan.lighting -> Lighting.set, plan.virtual ->
-- Lighting.setVirtual, plan.lodBias -> Lighting.setLodBias, plan.graphics = {group = level} -> Graphics.setGroup,
-- plan.resolutionScale, plan.gi -> Graphics.setGlobalIllumination. Natives are Z up (x east, y north, z up).
local f = io.open("Saved/gds-bench.lua", "rb")
if not f then return end
local chunk = load(f:read("a"), "gds-bench", "t", {})
f:close()
if not chunk then io.stdout:write("GDS-BENCH error plan-parse\n") io.stdout:flush() return end
local plan = chunk()
local out = plan.out or "Saved/bench"

-- io.stderr, not print: in a game the natives' print goes to the engine console; stderr is where the engine writes its NC_GPU_PROFILE
-- lines (profiler.cpp diagWrite), so the markers stay in order with them
local function log(s) io.stderr:write("GDS-BENCH ", s, "\n") io.stderr:flush() end
local function v3(t) return vec3(t[1], t[2], t[3]) end
local function now() return Async and Async.now and Async.now() or os.clock() end

local function apply()
  if plan.lighting and Lighting and Lighting.set then pcall(Lighting.set, plan.lighting) end
  if plan.virtual and Lighting and Lighting.setVirtual then pcall(Lighting.setVirtual, plan.virtual) end
  if plan.lodBias and Lighting and Lighting.setLodBias then pcall(Lighting.setLodBias, plan.lodBias) end
  if Graphics then
    if plan.quality then pcall(Graphics.setQuality, plan.quality) end
    for group, level in pairs(plan.graphics or {}) do pcall(Graphics.setGroup, group, level) end
    if plan.resolutionScale then pcall(Graphics.setResolutionScale, plan.resolutionScale) end
    if plan.gi then pcall(Graphics.setGlobalIllumination, plan.gi) end
    if plan.reflections then pcall(Graphics.setReflections, plan.reflections) end
    pcall(Graphics.setVSync, false)
    if Graphics.apply then pcall(Graphics.apply) end
  end
end

-- counters sampled every frame: pages of virtualized geometry, texture streaming (cumulative -> deltas in bench.py)
local function sample()
  local vs = Lighting and Lighting.getVirtualStats and Lighting.getVirtualStats() or {}
  local as = Async and Async.getStats and Async.getStats() or {}
  return vs.pageLoadsFrame or 0, vs.pageRequestsFrame or 0, vs.pageEvictionsFrame or 0, vs.poolUsedMB or 0,
    as.textureUploads or 0, as.textureMB or 0, as.textureWantedMB or 0, as.streamingTextures or 0, as.pending or 0
end

local csv = {}
local shotTaken = false
local function row(name, k, t, ms)
  local a, b, c, d, e, g, h, i, j = sample()
  local dc, ii, cpu = "", "", ""
  if k % 15 == 0 and Lighting and Lighting.getStats then   -- the big table: every 15 frames
    local s = Lighting.getStats()
    dc, ii, cpu = s.drawCalls or "", s.instancedItems or "", s.cpuFrameMs and ("%.2f"):format(s.cpuFrameMs) or ""
  end
  csv[#csv + 1] = ("%s,%d,%.3f,%.3f,%d,%d,%d,%.1f,%d,%.1f,%.1f,%d,%d,%s,%s,%s"):format(name, k, t, ms, a, b, c, d, e, g, h, i, j, dc, ii, cpu)
end

local function frames(name, seconds, step)
  -- step(alpha 0..1, frame) moves the camera; one row per frame
  log("begin " .. name)
  local t0, last, k = now(), now(), 0
  while true do
    local t = now() - t0
    if t >= seconds then break end
    step(t / seconds, k)
    Wait(0)
    local n = now()
    k = k + 1
    row(name, k, n - t0, (n - last) * 1000)
    last = n
  end
  log("end " .. name .. " frames=" .. k)
end

local function look(pos, target)
  SetCameraPosition(pos)
  SetCameraLookAt(target)
end

local function targetPos(s)
  if type(s.target) == "table" then return v3(s.target) end
  local e = s.target and GetEntityByName(s.target)
  if e and DoesEntityExist(e) then return GetEntityPosition(e) end
  return nil
end

CreateThread(function()
  log("start label=" .. tostring(plan.label))
  apply()
  -- warm up: wait for the level's async loads, then a fixed time (shader cache, first streaming)
  local w0 = now()
  while now() - w0 < (plan.maxLoadWait or 120) do
    local as = Async and Async.getStats and Async.getStats() or {}
    if (as.pending or 0) == 0 and now() - w0 > 2 then break end
    Wait(0)
  end
  local w1 = now()
  while now() - w1 < (plan.warmup or 5) do Wait(0) end
  log("warm loadWait=" .. ("%.1f"):format(w1 - w0))
  for _, s in ipairs(plan.scenarios or {}) do
    if s.kind == "view" then
      local p, l = v3(s.position), v3(s.lookAt)
      frames(s.name, s.seconds or 6, function() look(p, l) end)
      if plan.shot and not shotTaken then   -- the picture of the first view: bench.py compares it with base (A1, H8)
        look(p, l) Wait(0) Wait(0)
        shotTaken = TakeScreenshot and TakeScreenshot(plan.shot)
        log("shot " .. tostring(shotTaken) .. " " .. plan.shot)
      end
    elseif s.kind == "fly" then
      local pts, total, seg = s.points, 0, {}
      for i = 1, #pts - 1 do
        local d = Distance(v3(pts[i][1]), v3(pts[i + 1][1]))
        seg[i] = d
        total = total + d
      end
      frames(s.name, total / (s.speed or 8), function(a)
        local want, i = a * total, 1
        while i < #seg and want > seg[i] do want = want - seg[i] i = i + 1 end
        local u = seg[i] > 0 and want / seg[i] or 0
        look(Lerp(v3(pts[i][1]), v3(pts[i + 1][1]), u), Lerp(v3(pts[i][2]), v3(pts[i + 1][2]), u))
      end)
    elseif s.kind == "approach" then
      local tp = targetPos(s)
      if not tp then
        log("skip " .. s.name .. " target-not-found " .. tostring(s.target))
      else
        local dir = s.dir and Normalize(vec3(s.dir[1], s.dir[2], 0)) or vec3(0, -1, 0)
        local h = s.height or 1.7
        local lookAt = tp + vec3(0, 0, s.lookHeight or 1.0)
        for r = 1, s["repeat"] or 2 do   -- run 1 cold, run 2+ warm caches: the difference is the streaming
          frames(s.name .. "#" .. r, s.seconds or 8, function(a)
            local e = a * a * (3 - 2 * a)
            local d = (s.from or 60) + ((s.to or 2) - (s.from or 60)) * e
            look(tp - dir * d + vec3(0, 0, h), lookAt)
          end)
          -- back off and wait a little so run 2 starts far again
          local back = now()
          while now() - back < 1.5 do look(tp - dir * (s.from or 60) + vec3(0, 0, h), lookAt) Wait(0) end
        end
      end
    end
  end
  local fh = io.open(out .. ".csv", "w")
  if fh then
    fh:write("scenario,frame,t,ms,pageLoads,pageRequests,pageEvictions,poolUsedMB,texUploads,texMB,texWantedMB,streamingTextures,asyncPending,drawCalls,instancedItems,cpuFrameMs\n")
    fh:write(table.concat(csv, "\n"), "\n")
    fh:close()
  else
    log("error cannot-write " .. out .. ".csv")
  end
  log("DONE rows=" .. #csv)
  io.stdout:flush()
  -- the engine's own exit (the main loop ends, the renderer shuts down); os.exit skips that and, with NC_PROFILE_REPORT on,
  -- crashes in the report written by an exit handler (NUCLEON-ENGINE-NOTES A6)
  if type(exit) == "function" then exit() elseif QuitGame then QuitGame() else os.exit(0) end
end)
