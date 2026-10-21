-- Repro-first fix (GameDeveloperSkill, workers.md PHASE iterate-gate "Repro prima del fix").
-- Copy to Content/Scripts/test_bug_<key>.lua (key = the issue key of the wave / owner note), fill the three parts, then:
--   1. run it on the CURRENT build: it must FAIL with the numbers of the bug (that is the proof the bug is real and that
--      the test sees it): ncli play-test --expect "GDS-TEST bug_<key> FAIL"
--   2. fix the cause (never the test)
--   3. run it again: PASS, plus the whole suite (no regression): ncli play-test --expect "GDS-TEST DONE pass=<all> fail=0"
-- Both outputs go in the gate (`repro: {before: FAIL <reason>, after: PASS}`). The test stays in the suite forever:
-- the bug can not come back unnoticed. Delete this header comment in the copy.
-- covers: Content/Scripts/<the system the bug is in>.lua

exports.gds_test:Register("bug_KEY", function(t)
  -- 1. ARRANGE: the state the player was in (from the report: where, what they held, which perk). Real systems only:
  --    move the pawn with t.hold, trigger the game's own events; never set the result directly.
  local pawn = t.pawn()
  t.waitFor("the pawn on the ground", 5, function() return IsCharacterGrounded(pawn) end)

  -- 2. ACT: the input that showed the bug, from EVERY side the player meets it (front, side, behind; still, running)
  t.hold("W", 0.5)

  -- 3. ASSERT: the rule the game must keep, with the measured numbers in the message
  local p = GetEntityPosition(pawn)
  t.check(p.z > -1, ("fell through the floor: z = %.2f"):format(p.z))
end)
