-- GDS ground probe for `ncli.py lint --play` (GameDeveloperSkill, references/nucleon-loop.md "Lint", references/scene-lint.md).
-- Runs only when Saved/gds-probe.lua exists (ncli writes it just before Play and deletes it after Stop): for every listed
-- model/actor/shape it measures the real ground with Raycast (terrain, models and shapes are static colliders in Play)
--   under:  the first surface below the bottom of the object, not itself -> floating when bottom - under > tol
--   around: the median GROUND (terrain + the ids ncli marks as ground) just outside the footprint, from above,
--           passing through other objects                              -> underground when the top is below it,
--                                                                         or when more than half of the height is sunk
-- and prints one line per problem, then "GDS-PROBE DONE probed=<n> floating=<n> underground=<n> noGround=<n>".
-- ncli then drops the floating objects that are held by something (resting on, or room parts joined to their room).
--
-- Passing through a solid: a ray that starts INSIDE a collider hits it at the start point (Nucleon engine behaviour), so
-- "1 cm below the hit" never leaves a solid thicker than the number of tries. The next ray starts just under the bottom
-- of the solid that was hit when ncli gave its bounds (`zlo`), else 0.25 m lower; at most 64 rays per measure.
local f = io.open("Saved/gds-probe.lua", "rb")
if not f then return end
local text = f:read("a")
f:close()
local chunk = load(text, "gds-probe", "t", {})
if not chunk then print("GDS-PROBE DONE probed=0 error=parse") return end
local req = chunk()
local tol = req.tol or 0.05
local zlo = req.zlo or {}          -- [entity id] = bottom z of its bounds (every solid ncli listed)
local TRIES, STEP, EPS = 64, 0.25, 0.002

local function json(t)
  local parts = {}
  for k, v in pairs(t) do
    local val = type(v) == "number" and ("%.3f"):format(v) or ("%q"):format(tostring(v))
    parts[#parts + 1] = ("%q:%s"):format(k, val)
  end
  table.sort(parts)
  return "{" .. table.concat(parts, ",") .. "}"
end

local isGround, isTerrain = {}, {}
for _, id in ipairs(req.ground or {}) do isGround[id] = true end
for _, id in ipairs(req.terrain or {}) do isTerrain[id] = true end

-- where the next ray starts after a hit that is passed through
local function nextStart(hit, fromZ)
  local z = hit.position.z
  local lo = hit.entity ~= nil and zlo[hit.entity] or nil
  if lo and lo < z - EPS then return lo - EPS end              -- jump under the solid
  if fromZ - z < 0.001 then return z - STEP end               -- started inside a solid of unknown size
  return z - 0.01                                             -- entered from above: the next ray starts inside it
end

-- the first GROUND surface below a point: hits on other objects (neighbour walls, props, the object itself) are passed
-- through, so a wall next to a wall is not "sunk"; a ground ENTITY (not the terrain) above the object's top (a floor of
-- the storey above, a balcony) is a roof, not the ground, and is passed through too
local function groundBelow(x, y, z, top)
  local fz = z
  for _ = 1, TRIES do
    local hit = Raycast(vec3(x, y, fz), vec3(x, y, fz - 400))
    if not hit then return nil end
    -- the terrain (the landscape entity, or no entity) is the ground even above the top: a buried object
    if hit.entity == nil or isTerrain[hit.entity] then return hit.position.z end
    if isGround[hit.entity] and hit.position.z <= top + tol then return hit.position.z end
    fz = nextStart(hit, fz)
  end
  return nil
end

-- the first surface below the bottom of an object that is not the object itself, and what it is
local function supportBelow(id, x, y, bottom, height)
  -- start above the bottom by half the height (at most 0.5 m): a prop sunk a little into the terrain must not start
  -- the ray under the surface (a heightfield is one sided)
  local fz = bottom + math.min(0.5, math.max(0.03, height * 0.5))
  for _ = 1, TRIES do
    local hit = Raycast(vec3(x, y, fz), vec3(x, y, bottom - 400))
    if not hit then return nil end
    if hit.entity ~= id then return hit.position.z, hit.entity end
    fz = math.min(nextStart(hit, fz), bottom - EPS)
  end
  return nil
end

local function median(list)
  if #list == 0 then return nil end
  table.sort(list)
  return list[math.floor((#list + 1) / 2)]
end

CreateThread(function()
  Wait(0)   -- the level and its colliders are made in the first frame
  Wait(0)
  local floating, underground, noGround = 0, 0, 0
  for _, it in ipairs(req.items) do
    local lo, hi = it.lo, it.hi
    local cx, cy = (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2
    local hx, hy = (hi[1] - lo[1]) / 2 + 0.15, (hi[2] - lo[2]) / 2 + 0.15
    local around = {}
    for _, d in ipairs({{-1, -1}, {1, -1}, {1, 1}, {-1, 1}}) do
      local z = groundBelow(cx + d[1] * hx, cy + d[2] * hy, hi[3] + 50, hi[3])
      if z then around[#around + 1] = z end
    end
    local ground = median(around)
    local height = hi[3] - lo[3]
    local under, on = supportBelow(it.id, cx, cy, lo[3], height)
    if ground and (hi[3] < ground - tol or (ground - lo[3]) > 0.5 * height + tol) then
      underground = underground + 1
      print("GDS-PROBE underground " .. json({name = it.name, id = it.id, sunk = ground - lo[3], height = height}))
    elseif under and lo[3] - under > tol and (not ground or ground < lo[3] - tol) then
      floating = floating + 1
      print("GDS-PROBE floating " .. json({name = it.name, id = it.id, gap = lo[3] - under, on = on or "terrain"}))
    elseif not under and not ground then
      noGround = noGround + 1
      print("GDS-PROBE noGround " .. json({name = it.name, id = it.id}))
    end
  end
  print(("GDS-PROBE DONE probed=%d floating=%d underground=%d noGround=%d"):format(#req.items, floating, underground, noGround))
end)
