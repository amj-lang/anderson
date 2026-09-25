#!/usr/bin/env python3
"""Append one JSON line per finished anderson run, and summarize them — the evidence for tuning
the tier thresholds and crew patterns from real runs instead of guesses.

usage: runlog.py <task-dir> --mode gated|auto --outcome shipped|aborted:<reason> [--pr URL]
       runlog.py --summary
Log: $ANDERSON_RUNLOG, default ~/.claude/anderson/runs.jsonl. Local only, never sent anywhere.

ponytail: outcome is what's known when the run ends; post-merge bugs and reverts aren't tracked.
Add a field when a label or revert detector exists to feed it.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter

LOG = os.path.expanduser(os.environ.get("ANDERSON_RUNLOG", "~/.claude/anderson/runs.jsonl"))
PERSONAS = ("SERAPH", "NIOBE", "MEROVINGIAN")


def record(task_dir, mode, outcome, pr):
    with open(os.path.join(task_dir, "state.md"), encoding="utf-8") as f:
        text = f.read()
    block = text.split("<!-- STATE:START -->", 1)[-1].split("<!-- STATE:END -->", 1)[0]
    state = dict(m.groups() for m in re.finditer(r"^([a-z_]+):[ \t]*(.*?)[ \t]*$", block, re.M))
    tally = {p: [0, 0] for p in PERSONAS}
    for line in re.findall(r"crew_tally:(.*)", text):  # one line per review round
        for who, ok, raised in re.findall(r"(SERAPH|NIOBE|MEROVINGIAN)\s+(\d+)/(\d+)", line):
            tally[who][0] += int(ok)
            tally[who][1] += int(raised)
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "repo": os.path.basename(top.stdout.strip()) or None,
        "mode": mode,
        "outcome": outcome,
        "pr": pr,
        "state": state,
        "crew_tally": {p: v for p, v in tally.items() if v[1]},
        "diff_votes": re.findall(r"diff_vote_\S+:.*", text),
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
    lines += [f"{p:<12} seated {seated[p]:>3} · confirmed {ok[p]}/{raised[p]} raised"
              for p in PERSONAS]
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
    print(f"run logged → {LOG}")
