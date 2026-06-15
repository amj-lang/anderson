---
description: "Preview the full anderson pipeline UX (every stage banner + both gates). No agents, no tokens spent on the loop."
---
Print a dry-run of the whole loop and NOTHING else: do NOT invoke any subagent and do NOT touch any files. Output the five stage banners and the two gate lines, in order. Each banner is three lines — sigil, persona, and one quote picked from that stage's pool (vary the pick). Banner format:

  ⌐■-■  A N D E R S O N   ·   [N/4 or ✓] · [STAGE]
        [PERSONA] · [agent] · [model] · [effort] · [action]
        "[one quote from the pool]"

Print in exactly this order:

— 1/4 · PLAN · THE ARCHITECT · planner · opus · high · scoping → plan.md
  Pool: "Design twice, so reality only has to happen once." / "What you do not name in the plan will name itself in production." / "Scope is a fire: contain it or feed it."

— 2/4 · PLAN_REVIEW · THE ORACLE · plan-reviewer · opus · xhigh · editing plan.md
  Pool: "The flaw hides in the part everyone agreed not to question." / "A question carries more weight than any answer it returns." / "The map is not the territory, and the demo is not the system."
  Then the gate line: ■ GATE 1 · your turn. Read plan.md (## Diverged because). Approve: /anderson:approve-plan demo-task — or say "approved, go".

— 3/4 · IMPLEMENT · NEO · implementer · sonnet · medium · executing plan.md
  Pool: "Make it small enough to be wrong cheaply." / "Ship the truth, not the hope." / "One reviewable step beats ten clever ones."

— 4/4 · DIFF_REVIEW · AGENT SMITH · reviewer · opus · xhigh · read-only diff review
  Pool: "Your green tests are a comfort, not a verdict." / "Untested is unknown, and unknown is unsafe." / "Every assumption is a door you left unlocked."
  Then the gate line: ■ GATE 2 · awaiting you. Read diff-review.md AND the diff. Ship: /anderson:approve-diff demo-task · Rework: /anderson:rework demo-task

— ✓ · SHIP · THE ONE · welcome to the real world
  Pool: "Green is not understood; read what you merged." / "The gate is not an obstacle; it is the point." / "Review is how respect for the future is spelled."

End with: demo complete — no agents ran. (For a pure-shell, truly zero-token version, run bin/demo.sh in a terminal.)
