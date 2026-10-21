-- GDS test harness for Nucleon (GameDeveloperSkill, references/nucleon-loop.md "Tests").
-- Runs only when the environment variable NC_GDS_TEST is set (to 1, or to a comma separated list of test names).
-- Other scripts register tests with exports.gds_test:Register(name, fn); fn gets a context `t` with helpers and runs in
-- a thread (it may Wait). Every result is one log line the skill reads with `ncli.py play-test --expect "GDS-TEST DONE"`:
--   GDS-TEST <name> PASS (<seconds>s)   |   GDS-TEST <name> FAIL: <reason>   |   GDS-TEST DONE pass=<n> fail=<m>
-- In a packaged or standalone game the process exits with code 0 (all passed) or 3; Play In Editor only logs.
-- Natives are Z up (docs/api/NATIVES.md): x east, y north, z up, meters.
local wanted = os.getenv("NC_GDS_TEST")
local enabled = wanted ~= nil and wanted ~= "" and wanted ~= "0"
local only = {}
if enabled and wanted ~= "1" then for n in wanted:gmatch("[^,]+") do only[n] = true end end

local tests = {}
exports("Register", function(name, fn) tests[#tests + 1] = {name = name, fn = fn} end)
exports("Enabled", function() return enabled end)

if not enabled then return end

local function frameTime() local dt = GetFrameTime() return dt > 0 and dt or 1 / 30 end

local t = {}
function t.wait(seconds) local e = 0 while e < seconds do Wait(0) e = e + frameTime() end end
function t.waitFor(what, timeout, cond)
  local e = 0
  while not cond() do
    Wait(0)
    e = e + frameTime()
    if e > timeout then error("timeout waiting for " .. what, 0) end
  end
end
function t.check(cond, message) if not cond then error(message or "check failed", 0) end end
function t.near(a, b, tol, what)
  if math.abs(a - b) > (tol or 0.01) then error(("%s: %.3f, expected %.3f"):format(what or "value", a, b), 0) end
end
function t.pawn() return GetPlayerPawn(GetLocalPlayer()) end
-- hold a key for `seconds` as the player would (SimulateKey: a real event through the input actions, so the test also
-- covers Config/Input.lua and the pawn's own script); key names as SDL writes them: "W", "Space", "Left Shift", "E"
function t.hold(key, seconds)
  if not SimulateKey(key, true) then error("unknown key " .. key, 0) end
  local ok, err = pcall(t.wait, seconds)
  SimulateKey(key, false)
  Wait(0)
  if not ok then error(err, 0) end
end
function t.tap(key) t.hold(key, 0.1) end
-- feel numbers of the core verb (playtest.md feel baseline): one line `GDS-FEEL {"name":..., ...}` the worker stores
function t.feel(values)
  local parts = {}
  for k, v in pairs(values) do
    parts[#parts + 1] = ("%q:%s"):format(k, type(v) == "number" and ("%.4f"):format(v) or ("%q"):format(tostring(v)))
  end
  table.sort(parts)
  print("GDS-FEEL {" .. table.concat(parts, ",") .. "}")
end
-- frame times for `seconds` of play (optionally while holding a key: a walk through the level), one line
-- `GDS-PERF {"name":..., "p50_ms":..., "p95_ms":..., "p99_ms":..., "max_ms":..., "frames":...}` that `ncli play-test --fps N`
-- checks against the budget (1000 / N). Measured at time scale 1 (GetFrameTime is real frame time then).
function t.perf(name, seconds, key)
  local times, e = {}, 0
  if key then SimulateKey(key, true) end
  while e < seconds do
    Wait(0)
    local dt = GetFrameTime()
    if dt > 0 then times[#times + 1] = dt * 1000 e = e + dt else e = e + 1 / 30 end
  end
  if key then SimulateKey(key, false) end
  table.sort(times)
  local function q(p) return times[math.max(1, math.min(#times, math.ceil(#times * p)))] or 0 end
  print(("GDS-PERF {\"name\":%q,\"p50_ms\":%.2f,\"p95_ms\":%.2f,\"p99_ms\":%.2f,\"max_ms\":%.2f,\"frames\":%d}"):format(
    name, q(0.5), q(0.95), q(0.99), times[#times] or 0, #times))
end
function t.shot(name)
  local dir = os.getenv("NC_GDS_TEST_OUT")
  if dir and dir ~= "" then TakeScreenshot(dir .. "/" .. name .. ".png") end
end

CreateThread(function()
  t.waitFor("the pawn", 15, function() return GetLocalPlayer() and t.pawn() and DoesEntityExist(t.pawn()) end)
  t.wait(0.5)
  local pass, fail = 0, 0
  for _, test in ipairs(tests) do
    if next(only) == nil or only[test.name] then
      local start = GetGameTime()
      local ok, err = pcall(test.fn, t)
      if ok then
        pass = pass + 1
        print(("GDS-TEST %s PASS (%.1fs)"):format(test.name, GetGameTime() - start))
      else
        fail = fail + 1
        print(("GDS-TEST %s FAIL: %s"):format(test.name, tostring(err)))
      end
    end
  end
  print(("GDS-TEST DONE pass=%d fail=%d"):format(pass, fail))
  io.stdout:flush()
  if os.getenv("NC_GDS_TEST_EXIT") == "1" then os.exit(fail == 0 and 0 or 3) end
end)
