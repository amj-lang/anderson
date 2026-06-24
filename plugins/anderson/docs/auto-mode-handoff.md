# Handoff — Autonomous fix pipeline (Anderson `auto` mode + issue/trigger bot)

**Purpose:** port this design discussion into the right repos. Self-contained — a fresh session
in any destination repo can pick up from this doc alone.

**Companion doc:** `docs/auto-mode.md` (the full `auto` mode spec). Currently lives in
`gh-deploy-status/docs/` as a scratch location — **move it into the Anderson plugin repo** (see below).

---

## What we're building (one paragraph)

A chat message ("payment webhook fails on retry") becomes a tracked issue **and** kicks off an
autonomous Claude coding run that plans, writes a failing repro test, implements a fix, reviews itself
adversarially, and opens a **draft PR** — with a human only needed to merge. The autonomous coding
loop is a new **`auto` mode added to the existing Anderson plugin**. The chat→issue→trigger side is a
separate service, kept **source-agnostic** so it isn't bound to one issue tracker.

## Two planes (keep them separate)

| Plane | Runtime | Responsibility |
|---|---|---|
| **Issue / trigger plane** | Anthropic API + MCP connector, in a web service | Chat @mention → create issue, derive a `TaskSpec`, trigger the build plane |
| **Build plane** | **Claude Code** + Anderson plugin, in a runner | `/anderson:auto <TaskSpec>` → plan → test → implement → review → draft PR |

These are **different runtimes**. Anderson is a Claude Code plugin — it runs in Claude Code, **not**
the Anthropic API. The bot uses the API. Do not merge them into one process.

## The seam: `TaskSpec`

The build plane consumes only a generic `TaskSpec`. The issue/trigger plane (and any future source)
produces one. This is what keeps the whole thing tracker-agnostic.

```yaml
task:
  id:                  # stable id from source — used for the run lock
  title:
  body:
  acceptance_criteria: # optional; derived from body if absent (+ confidence flag)
  repo:
  scope_paths:         # optional; bounds planner + diff
```

---

## Destination repos

### Repo 1 — Anderson plugin (EXISTING)
The bulk of the design. Gets the new mode.

- **Add `/anderson:auto`** — a *non-halting orchestrator* skill. This is the only net-new code; it
  drives the existing subagents (`planner`, `plan-reviewer`, `implementer`, `reviewer`) and the
  rework loop end-to-end, swapping the human gates for agent panels + a CI veto.
- **Do NOT touch** the gated skills (`start`, `approve-plan`, `approve-diff`, `rework`) or the
  subagents — `auto` reuses them as-is.
- **Move `docs/auto-mode.md` here** as the living spec.
- Decision rationale (mode vs rewrite) and the full control flow are in `docs/auto-mode.md`.

### Repo 2 — issue/trigger bot (NEW, name TBD)
Was tentatively "triage-bot"; hold the name — keep this **agnostic**, not Linear-branded.

- Chat @mention webhook → create issue + derive `TaskSpec` → trigger Repo 1's runner.
- Source **adapters** live here (Linear, GitHub Issues, chat, CLI) — each maps a source event to a
  `TaskSpec`. **Adapters are deferred** — designed later; build the TaskSpec contract first.
- Stack (decided): **Python + FastAPI + `anthropic` SDK with MCP connector**.

---

## Decisions ledger

**Decided:**
- Add an `auto` **mode** to Anderson — do not rewrite. Shared subagents, two entry points.
- Success rate comes from **objective CI gate + independent adversarial panels + loop-until-clean** —
  NOT self-approval (self-approval lowers success rate).
- Keep **one** human gate: final PR merge. Draft PR only; never auto-merge; branch only.
- **Source-agnostic** via `TaskSpec`; trackers are adapters.
- Bot stack: Python + FastAPI + Anthropic SDK + **MCP connector** (not a `claude -p` subprocess).
- Workspace: fresh branch off latest default, isolated worktree/clone per run, clean-tree precondition.

**Rejected / parked:**
- "Claude answers its own gates" naive self-approval → rejected (inflates confidence, ships wrong).
- Managed Agents (CMA) as the build runtime → parked: can't run the Anderson *plugin* (CMA ≠ Claude
  Code); would mean reimplementing the gates.
- Repo name "triage-bot" → parked pending the agnostic decision.

## Open questions (resolve per repo)

1. **Runner** for the build plane — GitHub Actions (CI gate = the workflow itself, native `gh`) vs. a
   long-running worker. Affects how the suite runs (steps 2 & 7 in the spec).
2. **RED step** — always, or feature-exempt? (Bug fix → yes; feature → test encodes criteria.)
3. **Acceptance criteria** — require as input vs. always derive. Current default: derive-if-absent + flag.
4. **Panel size / threshold** — default 3 critics / majority-refute; tune later.
5. **Difficulty routing** — size the harness to task difficulty (v2?).

---

## Key technical facts (so a fresh session doesn't re-derive them)

**MCP connector (issue bot → tracker):**
- Needs **both** `mcp_servers=[{type:"url", name, url, authorization_token}]` **and**
  `tools=[{type:"mcp_toolset", mcp_server_name:<same name>}]`. Server alone = 400.
- Beta — pass `betas=["mcp-client-2025-11-20"]` on `client.beta.messages.create` (not the plain path).
- Linear hosted MCP URL: `https://mcp.linear.app/sse`. Auth is an **OAuth bearer token**, NOT a Linear
  API key (`lin_api_...` will not work as MCP auth — different system).

**Models / pricing (per 1M tokens, in/out):**
- `claude-opus-4-8` — $5 / $25. Default for plan/label/route judgment and the coding loop.
- `claude-sonnet-4-6` — $3 / $15. A/B candidate for the bot once the prompt is stable.
- Use bare model-ID strings, no date suffixes.

**Build plane safety boundaries (non-negotiable):**
- Draft PR only, never auto-merge; branch only (`anderson/auto/<task-id>-<slug>`).
- Baseline must be GREEN before any change (never fix on a broken tree).
- Test-tamper guard: freeze the RED test, reviewer rejects if it changed.
- Forbidden paths (CI config, `.github/`, secrets, lockfiles, migrations) unless the task is about them.
- Dependency/manifest changes → flag PR `needs-human`, no exceptions.
- Thrash breaker: findings must shrink each rework round; `max_rework_rounds` ≈ 3.
- Bail-to-human at the plan stage if the task is ambiguous/underspecified.
- Run lock per `task.id`; stage checkpoints for resume; per-run token/time budget cap.

**Secrets:** bot needs an Anthropic key + tracker MCP OAuth token. Build runner needs an Anthropic key
+ a repo-scoped GitHub token (contents + PR write). Do not share credentials across planes.

---

## Next steps (checklist)

**Anderson plugin repo:**
- [ ] Move `docs/auto-mode.md` into the repo.
- [ ] Resolve open questions 1–4.
- [ ] Build the `/anderson:auto` orchestrator skeleton (control flow calling existing subagents).
- [ ] Wire the panels (plan critics, blind diff reviewers), CI veto, rework/thrash loop.

**Issue/trigger bot repo:**
- [ ] Decide the agnostic name; create the repo.
- [ ] Scaffold FastAPI + Anthropic SDK MCP-connector handler (chat → issue).
- [ ] Define the `TaskSpec` contract + emit it from the chat flow.
- [ ] Stub one source adapter (defer the rest).
- [ ] Decide trigger transport to the build plane (e.g. `repository_dispatch` if runner = GH Actions).

**Cross-cutting:**
- [ ] Lock the runner choice (GH Actions vs worker) — it gates both planes.
