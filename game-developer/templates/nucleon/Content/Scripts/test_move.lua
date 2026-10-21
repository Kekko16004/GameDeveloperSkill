-- Example verb test (GameDeveloperSkill): holding W walks the pawn forward and it stays on the ground. Copy the pattern per verb:
-- one file test_<verb>.lua, one or more Register calls, numbers in the failure message.
exports.gds_test:Register("move_forward", function(t)
  local pawn = t.pawn()
  t.waitFor("the pawn on the ground", 5, function() return IsCharacterGrounded(pawn) end)
  local p0 = GetEntityPosition(pawn)
  t.hold("W", 1.0)                      -- Move forward through the real binding (Config/Input.lua)
  t.wait(0.3)
  local p1 = GetEntityPosition(pawn)
  local moved = Distance(vec3(p0.x, p0.y, 0), vec3(p1.x, p1.y, 0))
  t.check(moved > 1.5, ("moved %.2f m holding W for 1 s"):format(moved))
  t.check(IsCharacterGrounded(pawn), "the pawn left the ground")
end)
