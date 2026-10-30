# Nucleon performance diagnosis (optimization loop)

## 8b. Performance diagnosis: `tools/nucleon-bench`
The loop and the budget are [../optimization.md](../optimization.md); the measurement is `ncli bench` (stored baseline, p50/p95/p99, `trusted` flag); this section is the deeper tool for a miss.

When `play-test --fps` fails on the real GPU, or the owner reports drops: don't guess. `bench.py grab-view` (the spot from the
open editor) → `bench.py run --only <H>` (one change per config against base: shadows, LOD, foliage, GI, texture and page
streaming, the GPU-driven paths, resolution) → `analyze` (REPORT.md with verdicts) → `plan` (EXECUTION-PLAN.md: briefs with a
ready-made prompt for Claude Code in the NucleonEngine repository). Engine bugs and the K1-K5 briefs:
`docs/NUCLEON-ENGINE-NOTES.md`. In the meantime the game works around them: `NC_GPU_DRIVEN=0` if repeated props come out wrong
(A1), `instances` for repeated props once they have been run. The bench has H10 (the material system: models, sets, offset,
layers, deferred models) to tell what the new materials cost.
