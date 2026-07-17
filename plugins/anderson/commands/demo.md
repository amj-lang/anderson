---
description: "Preview the full anderson pipeline UX (every stage banner + both gates). No agents, no tokens spent on the loop."
---
Print a dry-run of the whole loop and NOTHING else: do NOT invoke any subagent
and do NOT touch any files. Print the five framed stage banners and the two gate
lines, in order, in the SAME framed format the live loop uses — one quote picked
at random from each stage's pool (vary the pick). Then the SHIP banner. Format:

  ╭─ ⌐■-■  [STAGE] · [N/5 or ✓] · [PERSONA] · [model/effort or tagline]
  │  "[one quote from the pool]"
  ╰─

Print in exactly this order (sub-bullet = quote pool to pick from):

╭─ ⌐■-■  PLAN · 1/5 · THE ARCHITECT · opus/high
  Pool: "Design twice, so reality only has to happen once." / "What you do not name in the plan will name itself in production." / "Scope is a fire: contain it or feed it."

╭─ ⌐■-■  GRILL · 2/5 · THE INTERROGATOR · you
  Pool: "Every unanswered question is a bug with a delay." / "The plan you cannot defend out loud is not yet a plan." / "Pin every fork before the code picks one for you."
  (opens with a one-line manifest — `grill · N questions · a🔴 b🟡 c🟢` + a rule — then asks 🔴 → 🟡 one/few at a time, each as a 3-line card `🔴 n/N ▰▰▱▱▱▱▱▱▱▱` / question / → recommendation, batches 🟢 at the end; questions are triaged from the plan's own decision tree, ✅ acceptance criteria (`derived` rows are 🔴 — confirm/edit/drop), 💥 blast radius, 📈 scorecard, and 🧯 error-handling `needs-context` rows — the blast-radius walk is where completeness gets challenged; each row you defer is recorded under state.md `## ❓ Open questions`)

╭─ ⌐■-■  PLAN_REVIEW · 3/5 · THE ORACLE · opus/xhigh
  Pool: "The flaw hides in the part everyone agreed not to question." / "A question carries more weight than any answer it returns." / "The map is not the territory, and the demo is not the system."
  Then the gate marker (live runs print a TL;DR card — what · criteria/proof counts ·
  scorecard · verdict — so plan.md only needs opening when a line raises doubt):
  ﾊﾐﾐ 0ｺ1  🔴 G A T E  1 · YOUR TURN  1ｺ0 ﾐﾐﾊ
  ⌐■-■  Add CSV export to the briefs table
        criteria 5 (2 ticket · 2 design · 1 derived) · proof: 3 test · 1 visual · 1 e2e
        scorecard: Risk 4 · Confidence 8 · Coupling 3 · Reversibility 9
        verdict ship → /anderson:approve-plan demo-task — or "approved, go"

╭─ ⌐■-■  IMPLEMENT · 4/5 · NEO · sonnet/medium
  Pool: "Make it small enough to be wrong cheaply." / "Ship the truth, not the hope." / "One reviewable step beats ten clever ones."

╭─ ⌐■-■  DIFF_REVIEW · 5/5 · AGENT SMITH · opus/xhigh
  Pool: "Your green tests are a comfort, not a verdict." / "Untested is unknown, and unknown is unsafe." / "Every assumption is a door you left unlocked."
  Then the gate marker:
  ﾊﾐﾐ 0ｺ1  🔴 G A T E  2 · AWAITING YOU  1ｺ0 ﾐﾐﾊ
  ⌐■-■  criteria 5/5 proven (all)
        verdict ship → read the diff + plan.md ## 🔭 Review, then
        /anderson:approve-diff demo-task to ship, or /anderson:rework demo-task
  (ship builds a lean PR — What & why · criteria table with evidence · scorecard, Setup/Open-questions only when non-empty, full reviewed plan in a collapse — then deletes the gitignored scratch; the PR is the durable record)

╭─ ⌐■-■  SHIP ✓ · THE ONE · welcome to the real world
  Pool: "Green is not understood; read what you merged." / "The gate is not an obstacle; it is the point." / "Review is how respect for the future is spelled."

End with: demo complete — no agents ran. (For a pure-shell, truly zero-token version, run bin/demo.sh in a terminal.)
