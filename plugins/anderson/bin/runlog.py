#!/usr/bin/env python3
"""Append one JSON line per finished anderson run, and summarize them — the evidence for tuning
the tier thresholds and crew patterns from real runs instead of guesses.

usage: runlog.py <task-dir> --mode gated|auto --outcome shipped|aborted:<reason> [--pr URL]
       runlog.py --summary
Log: $ANDERSON_RUNLOG, default ~/.claude/anderson/runs.jsonl. Local only, never sent anywhere.
Each line also carries `cost` {stage: {tokens, ms}}, `tokens`, `duration_ms` (from the band's ledger
<task-dir>/cost.jsonl, which record consumes: removed after the line is appended), `scorecard` and
`tier_line` (from plan.md). Missing sources omit the cost keys / give {} and None.

ponytail: outcome is what's known when the run ends; post-merge bugs and reverts aren't tracked.
Add a field when a label or revert detector exists to feed it.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter
from statistics import median

LOG = os.path.expanduser(os.environ.get("ANDERSON_RUNLOG", "~/.claude/anderson/runs.jsonl"))
PERSONAS = ("SERAPH", "NIOBE", "MEROVINGIAN")


def tally(text, key):
    """Sum `<key>: SERAPH 1/2 · …` lines (one per review round) into {persona: [confirmed, raised]}."""
    out = {p: [0, 0] for p in PERSONAS}
    for line in re.findall(rf"\b{key}:(.*)", text):
        for who, ok, raised in re.findall(r"(SERAPH|NIOBE|MEROVINGIAN)\s+(\d+)/(\d+)", line):
            out[who][0] += int(ok)
            out[who][1] += int(raised)
    return {p: v for p, v in out.items() if v[1]}


def _num(v):
    # Bounded: a 10**400 ledger value would crash `--summary` (median/1000) and json.dumps (int digit limit).
    return isinstance(v, (int, float)) and not isinstance(v, bool) and (isinstance(v, int) or math.isfinite(v)) and 0 <= v < 2 ** 53


def cost(task_dir):
    """Fold the band ledger into {stage: {tokens, ms}}; ms = union of the stage's seat intervals (gaps between reworks excluded)."""
    seats = {}
    try:
        with open(os.path.join(task_dir, "cost.jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if (isinstance(d, dict) and isinstance(d.get("stage"), str)
                        and all(_num(d.get(k)) for k in ("tokens", "start", "end"))):
                    seats.setdefault(d["stage"], []).append(d)
    except (OSError, ValueError):
        pass
    return {s: {"tokens": sum(d["tokens"] for d in ds), "ms": _union_ms(ds)} for s, ds in seats.items()}


def _union_ms(ds):
    total, hi = 0, None
    for d in sorted(ds, key=lambda d: d["start"]):
        lo = d["start"] if hi is None else max(d["start"], hi)
        total += max(0, d["end"] - lo)
        hi = d["end"] if hi is None else max(hi, d["end"])
    return total


def plan_facts(task_dir):
    """Planner Scorecard numbers and the `**Tier:**` line from plan.md ({} / None when absent)."""
    try:
        with open(os.path.join(task_dir, "plan.md"), encoding="utf-8") as f:
            plan = f.read()
    except (OSError, ValueError):
        return {}, None
    score = {}
    for m in re.finditer(r"^\|\s*(Risk|Horizontality|Testability|Reversibility|Confidence|Coupling)\b[^|]*\|\s*(\d{1,3})\b", plan, re.M):
        score.setdefault(m[1].lower(), int(m[2]))
    t = re.search(r"^\*\*Tier:\*\*\s*(.*)$", plan, re.M)
    return score, t[1].strip() if t else None


def record(task_dir, mode, outcome, pr):
    with open(os.path.join(task_dir, "state.md"), encoding="utf-8") as f:
        text = f.read()
    block = text.split("<!-- STATE:START -->", 1)[-1].split("<!-- STATE:END -->", 1)[0]
    state = dict(m.groups() for m in re.finditer(r"^([a-z_]+):[ \t]*(.*?)[ \t]*$", block, re.M))
    ledger = cost(task_dir)
    score, tier_line = plan_facts(task_dir)
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    extra = {"cost": ledger, "tokens": sum(c["tokens"] for c in ledger.values()),
             "duration_ms": sum(c["ms"] for c in ledger.values())} if ledger else {}
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "repo": os.path.basename(top.stdout.strip()) or None,
        "mode": mode,
        "outcome": outcome,
        "pr": pr,
        "state": state,
        "crew_tally": tally(text, "crew_tally"),
        "plan_tally": tally(text, "plan_tally"),
        "diff_votes": re.findall(r"diff_vote_\S+:.*", text),
        **extra,
        "scorecard": score,
        "tier_line": tier_line,
    }


def rework_rounds(state):
    if state.get("rework_round", "").isdigit():
        return int(state["rework_round"])
    return max(int(state["iteration"]) - 1, 0) if state.get("iteration", "").isdigit() else 0


def summary(runs):
    out = Counter(r["outcome"].split(":")[0] for r in runs)
    tiers = Counter(r["state"].get("tier", "?") for r in runs)
    seated, ok, raised = Counter(), Counter(), Counter()
    for r in runs:
        for p in PERSONAS:
            seated[p] += p in r["state"].get("crew", "")
            ok[p] += r["crew_tally"].get(p, [0, 0])[0]
            raised[p] += r["crew_tally"].get(p, [0, 0])[1]
    avg = sum(map(rework_rounds, (r["state"] for r in runs))) / len(runs)
    lines = [
        f"runs {len(runs)} · " + " · ".join(f"{k} {v}" for k, v in sorted(out.items())),
        "tiers " + " · ".join(f"{k} {v}" for k, v in sorted(tiers.items())),
        f"rework rounds avg {avg:.1f}",
    ]
    for t in sorted(tiers):
        rs = [r for r in runs if r["state"].get("tier", "?") == t]
        tok = [r["tokens"] for r in rs if "tokens" in r]
        dur = [r["duration_ms"] for r in rs if "duration_ms" in r]
        lines.append(f"{t:<9} runs {len(rs):>3} · tokens med {f'{median(tok) / 1000:.0f}k' if tok else 'n/a'}"
                     f" · time med {f'{median(dur) / 60000:.0f}m' if dur else 'n/a'}"
                     f" · rework {sum(rework_rounds(r['state']) > 0 for r in rs)}/{len(rs)}")
    lines += [f"{p:<12} seated {seated[p]:>3} · confirmed {ok[p]}/{raised[p]} raised"
              for p in PERSONAS]
    plan = Counter()  # runs logged before the plan crew have no plan_tally
    for r in runs:
        for p, (c, n) in r.get("plan_tally", {}).items():
            plan[p, 0] += c
            plan[p, 1] += n
    lines += [f"{p:<12} plan review · confirmed {plan[p, 0]}/{plan[p, 1]} raised"
              for p in PERSONAS if plan[p, 1]]
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Append or summarize the anderson run log.")
    ap.add_argument("task_dir", nargs="?")
    ap.add_argument("--mode", choices=("gated", "auto"))
    ap.add_argument("--outcome")
    ap.add_argument("--pr", default=None)
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.summary:
        try:
            with open(LOG, encoding="utf-8") as f:
                runs = [json.loads(line) for line in f if line.strip()]
        except FileNotFoundError:
            runs = []
        print(summary(runs) if runs else f"no runs logged yet ({LOG})")
        sys.exit(0)
    if not (a.task_dir and a.mode and a.outcome):
        ap.error("need <task-dir> --mode --outcome (or --summary)")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    rec = record(a.task_dir, a.mode, a.outcome, a.pr)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    try:  # folded into the log: a re-run of the same slug starts a fresh ledger
        os.remove(os.path.join(a.task_dir, "cost.jsonl"))
    except OSError:
        pass
    print(f"run logged → {LOG}")
