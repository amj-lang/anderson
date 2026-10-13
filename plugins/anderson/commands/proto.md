---
description: "Prototype a visual question: 2-3 throwaway variants that look nothing alike (ASCII for terminal UIs, HTML for web), you pick one. Works inside a task or on its own."
argument-hint: <what to prototype> [--task <slug>] [--n 2|3]
allowed-tools: Bash(mkdir:*), Bash(cat:*), Bash(open:*), Bash(xdg-open:*), Bash(cp:*), Bash(grep:*), Bash(echo:*)
---
Parse "$ARGUMENTS": `--task <slug>` (task key = last `/`-segment) and `--n` (default 3, max 3)
are optional; the rest is the question, e.g. "pause screen" or "fleet row for a sliced task".

1. OUT DIR — with a task: `feature-research/<task>/proto/<q>/`; without: `feature-research/proto/<q>/`,
   where `<q>` is a short kebab slug of the question. `mkdir -p` it. Make sure `.gitignore` has
   `feature-research/` (append when absent), so nothing here ever reaches a commit.
2. CONTEXT — with a task, collect the settled decisions: `## ✅ Decisions` rows marked ✓ and the
   `[answered]` lines in state.md `## ❓ Open questions`, plus the plan's 🎯 What. Without a task,
   the settled decisions are whatever this conversation already fixed. Target: terminal when the
   question is about CLI/TUI/terminal output or the repo's UI is a terminal app, web when it is a
   page/screen/component; ask me in one line only when it is genuinely ambiguous.
3. Print this banner as the LAST line before the agent call, then invoke the **prototyper**
   subagent with: the question, target, n, out dir, the settled decisions, and the repo root.
   ```
     ╭─ ⌐■-■  PROTO · THE CONSTRUCT · sonnet/medium · <n> variants · <target>
     │  "Many paths, one door: look before you walk it."
     ╰─
   ```
4. SHOW — print the variant table from `<out>/README.md`. Terminal target: `cat` each `<X>.txt`
   under a `── A · <axis> ──` rule, verbatim, in a code block. Web target: `open` (macOS) or
   `xdg-open` each `<X>.html`, and print the paths. Then ask:
   `pick: A / B / C · mix (e.g. "A layout, C detail row") · again <steer>`
5. PICK —
   - `again <steer>` → re-invoke the prototyper once with the steer added (same out dir, new
     variants overwrite); a third round means the question is not ready, say so and stop.
   - a mix → re-invoke once asking for that single combined variant `M`, then treat it as picked.
   - a letter (or `M`) → with a task: `cp` the variant into `feature-research/<task>/design/`
     as `proto-<q>.<ext>`, append its Inventory lines to `design/inventory.md` under
     `## proto: <q>`, and record `[answered] <question> → variant <X>: <idea> (proto)` in state.md
     `## ❓ Open questions`. When called from the grill, the grill folds it into plan.md as a
     `source: design` criterion and a ✓ Decisions row, like any other answer. Without a task:
     answer in one line (`picked <X>: <idea>`) and leave the files where they are.
6. Done line: `🎨 proto · <q> · picked <X> · <path>` — or `not ready` when it stopped at step 5.
