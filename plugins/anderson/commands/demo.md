---
description: "Preview the full anderson pipeline UX (the crew band at every stage + both gates). No agents, no tokens spent on the loop."
---
Print a dry-run of the whole loop and NOTHING else: do NOT invoke any subagent
and do NOT touch any files. Print, verbatim and in order, the frames and the two gate
cards below, each in its own code block under its `──` title.

This is the crew band that sits just above the prompt during a live run (colors omitted):

```
── 1. plan: THE ARCHITECT working
⌐■-■ ◐○○○○○○ plan 1/7 · 3:00 · I: 412k / O: 10k  1 live ──────────────────────────────────────────────────────
┌ THE ARCHITECT ⠸ ───────────────┐
│ opus/medium    3:00            │
└ ▸ Read api/limiter.py ─────────┘

── 2. grill: you answer, in the transcript
⌐■-■ ●◐○○○○○ grill 2/7 · 5:00 · I: 1.3M / O: 22k ─────────────────────────────────────────────────────────────
┌ THE ARCHITECT ✓ ───────────────┐
│ opus/medium    3:12  1101k tok │
└ ✓ done ────────────────────────┘

── 3. plan_review done, gate
⌐■-■ ●●◐○○○○ your turn ▸ /anderson:approve-plan · 9:00 · I: 2.0M / O: 41k ────────────────────────────────────
┌ THE ORACLE ✓ ──────────────────┐
│ opus/high      4:00  640k tok  │
└ ✓ done ────────────────────────┘

── 4. implement: NEO working
⌐■-■ ●●●◐○○○ implement 4/7 · 14:00 · I: 3.4M / O: 88k  1 live ────────────────────────────────────────────────
┌ NEO ⠸ ─────────────────────────┐
│ sonnet/medium 14:00            │
└ ▸ Edit api/limiter.py ─────────┘

── 5. repair: TRINITY stalled (only when tests go red)
⌐■-■ ●●●●◐○○ repair 5/7 · 18:30 · I: 4.1M / O: 102k  1 live ──────────────────────────────────────────────────
┌ TRINITY ⚠ ─────────────────────┐
│ sonnet/high   18:30            │
└ ⚠ stalled 2:30 · Bash pytest …─┘

── 6. diff_review: crew of 4, mixed
⌐■-■ ●●●●●◐○ diff_review 6/7 · 4:00 · I: 5.6M / O: 131k  2 live ──────────────────────────────────────────────
┌ NIOBE ⠸ ────────── performance ┐ ┌ THE MEROVINGIAN ⠸ ──────── api ┐ [ SMITH ✗ 1 blocking ]
│ opus/medium    4:00            │ │ opus/medium    4:00            │ [ SERAPH ✓ 0 blocking ]
└ ▸ Grep rate_limit ─────────────┘ └ ▸ Read api/routes.py ──────────┘

── 7. diff_review gate: blocking → rework
⌐■-■ ●●●●●◐○ your turn ▸ /anderson:rework · 6:00 · I: 6.2M / O: 140k ─────────────────────────────────────────
┌ AGENT SMITH ✗ ─────────────────┐ ┌ SERAPH ✓ ──────────── security ┐
│ opus/xhigh     3:00  820k tok  │ │ opus/high      2:00  410k tok  │
└ ✗ 1 blocking · 2 nits ─────────┘ └ ✓ 0 blocking ──────────────────┘

── 8. shipped
⌐■-■ ●●●●●●● shipped · 31:00 · I: 7.9M / O: 176k ─────────────────────────────────────────────────────────────
```

The grill (frame 2) runs in the transcript: a one-line manifest — `grill · N questions · a🔴 b🟡 c🟢` + a rule — then 🔴 → 🟡 one/few at a time, each as a 3-line card `🔴 n/N ▰▰▱▱▱▱▱▱▱▱` / question / → recommendation, 🟢 batched at the end; questions come from the plan's own decision tree, ✅ acceptance criteria (`derived` rows are 🔴), 💥 blast radius, 📈 scorecard, and 🧯 error-handling `needs-context` rows; each row you defer lands under state.md `## ❓ Open questions`.

Gate 1 card (after frame 3; plan.md only needs opening when a line raises doubt):

```
🔴 GATE 1 · YOUR TURN
  Add CSV export to the briefs table
  criteria 5 (2 ticket · 2 design · 1 derived) · proof: 3 test · 1 visual · 1 e2e
  assumptions: 2 load-bearing · all confirmed ✓   (each criterion has its own proof)
  scorecard: Risk 4 · Confidence 8 · Coupling 3 · Reversibility 9
  tier NORMAL · plan_review opus/high · implement sonnet/medium · diff_review opus/high
  verdict ship → /anderson:approve-plan demo-task — or "approved, go"
```

Gate 2 card (after frame 7, on a clean review):

```
🔴 GATE 2 · AWAITING YOU
  criteria 5/5 proven (all)
  verdict ship → read the diff (`! git diff HEAD` · new files `! git status -s` ·
  fleet `o`) + plan.md ## 🔭 Review, then
  /anderson:approve-diff demo-task to ship, or /anderson:rework demo-task
```

(Ship builds the PR from the plan minus the how — What & why · criteria with evidence · design · how-to-test + config, with scorecard / blast radius / error handling in collapses; Open-questions only when non-empty — then deletes the gitignored scratch; the PR is the durable record.)

End with: demo complete — no agents ran.
