---
description: Run Play, verb tests, console/log, lint and screenshot report on the current project (any engine)
---

Load the `game-developer` skill and run references/playtest.md for the current project (engine from GDD.md, bridge from engines.md): $ARGUMENTS

Every GDD verb needs a test that actually ran plus a screenshot in screenshots/. Unity: `run_tests` + `editor_play`. Nucleon: `NC_GDS_TEST=1` + `python SKILL/scripts/ncli.py play-test --expect "GDS-TEST DONE pass=<n> fail=0" --shot screenshots/play.png` + `ncli lint`. Write docs/playtest.md. Fix console/log errors before claiming pass.
