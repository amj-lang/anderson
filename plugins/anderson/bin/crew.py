#!/usr/bin/env python3
"""Pick the review crew (the lens seats that join THE ORACLE or AGENT SMITH) from what the task touches.

Deterministic on purpose: routing is pattern matching, not a model call.
usage: crew.py <tier> [--hint lens,lens] [--plan plan.md] <file>...   (run from the repo root)
  diff review: files = the diff scope; changed lines come from `git diff HEAD`.
  plan review (--plan): files = plan.md "Files touched"; the plan's text stands in for changed
  lines, and only security + performance sit (leftovers needs a diff; the plan-reviewer's
  blast-radius check owns planned dead code).
prints one line per summoned lens: `<lens> <PERSONA> <agent> <model/effort> <reason>`, or `none`.
Every seat runs on opus; effort is frontmatter-only, so the effort picks the agent.

ponytail: regex over paths + changed lines; over-summons on a name match (cheap: one extra
seat), under-summons security only below HARD (the tier forces SERAPH from HARD up). At plan
review the code regexes scan prose too, so "select a row from the list" seats SERAPH: same trade.
"""
import argparse
import re
import subprocess
import sys

CODE = re.compile(r"\.(ts|tsx|js|jsx|mjs|cjs|py|go|rb|php|java|kt|cs|rs|swift|vue|svelte|sql)$")
SEC_PATH = re.compile(
    r"auth|login|session|passw|token|secret|permission|rbac|acl|oauth|jwt|crypto|middleware"
    r"|(^|/)api/|(^|/)routes?/|(^|/)controllers?/|(^|/)handlers?/|(^|/)\.env"
    r"|package(-lock)?\.json$|yarn\.lock$|pnpm-lock|requirements[^/]*\.txt$|pyproject\.toml$"
    r"|Dockerfile|\.github/workflows/", re.I)
SEC_CODE = re.compile(
    r"child_process|\bexec(Sync)?\(|\bspawn\(|subprocess|shell=True|\beval\(|new Function\("
    r"|dangerouslySetInnerHTML|\.innerHTML|\.raw\(|process\.env|os\.environ|document\.cookie"
    r"|set-cookie|\bjwt\b|password|secret|\bredirect\(|pickle\.loads|yaml\.load\(|\bcors\b"
    r"|\b(SELECT|INSERT|UPDATE|DELETE)\b.*\b(FROM|INTO|SET|WHERE)\b", re.I)
PERF_PATH = re.compile(
    r"(^|/)(db|database|models?|repositor(y|ies)|quer(y|ies)|cache|workers?|jobs?|queues?)(/|\.)", re.I)
PERF_CODE = re.compile(
    r"\buse(Layout)?Effect\(|setInterval\(|\bwhile\s*\(|readFileSync|execSync|Promise\.all\("
    r"|\.(findMany|findAll|aggregate|query)\(|\bprisma\.|\bknex\b|sequelize|typeorm|mongoose"
    r"|\bredis\b|\bJOIN\b", re.I)

PERSONA = {"security": "SERAPH", "performance": "NIOBE", "leftovers": "MEROVINGIAN"}


def changed(path):
    """(added, removed) lines of one file: tracked -> diff vs HEAD; untracked -> all added."""
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", path],
                             capture_output=True).returncode == 0
    if not tracked:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return f.read().splitlines(), []
        except OSError:
            return [], []
    out = subprocess.run(["git", "diff", "HEAD", "--", path],
                         capture_output=True, text=True).stdout.splitlines()
    added = [l[1:] for l in out if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:] for l in out if l.startswith("-") and not l.startswith("---")]
    return added, removed


PLAN_LENSES = ("security", "performance")


def crew(tier, files, hints=(), plan=None):
    """plan: the plan.md lines at plan review (no diff yet), None at diff review."""
    hard = tier in ("hard", "critical")
    picks = {}
    if plan is not None:
        if any(SEC_CODE.search(l) for l in plan):
            picks["security"] = "plan text"
        if any(PERF_CODE.search(l) for l in plan):
            picks["performance"] = "plan text"
    for path in files:
        added, removed = changed(path) if plan is None else ([], [])
        if SEC_PATH.search(path):
            picks.setdefault("security", f"path {path}")
        elif any(SEC_CODE.search(l) for l in added):
            picks.setdefault("security", f"code in {path}")
        if PERF_PATH.search(path) or any(PERF_CODE.search(l) for l in added):
            picks.setdefault("performance", f"{path}")
        if CODE.search(path) and any(l.strip() for l in removed):
            picks.setdefault("leftovers", f"removed code in {path}")
    if hard:
        picks.setdefault("security", f"tier {tier}")
    for lens in hints:  # the plan's Crew hint: add-only, never removes a rule's pick
        picks.setdefault(lens, "hint from plan")
    if plan is not None:
        picks = {lens: why for lens, why in picks.items() if lens in PLAN_LENSES}
    seat = {"security": ("reviewer", "opus/high")}
    below = ("reviewer", "opus/high") if hard else ("reviewer-medium", "opus/medium")
    return [(lens, PERSONA[lens], *seat.get(lens, below), why) for lens, why in picks.items()]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pick the diff-review crew from what the diff touches.")
    ap.add_argument("tier")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--hint", default="", help="comma-separated lenses from the plan's Crew hint")
    ap.add_argument("--plan", help="plan.md: pick the plan-review crew instead of the diff crew")
    args = ap.parse_args()
    plan = None
    if args.plan:
        with open(args.plan, encoding="utf-8") as f:
            plan = f.read().splitlines()
    hints = [h.strip().lower() for h in args.hint.split(",") if h.strip().lower() not in ("", "none")]
    for h in hints:
        if h not in PERSONA:
            print(f"crew.py: ignoring unknown hint lens '{h}' (use {', '.join(PERSONA)})", file=sys.stderr)
    seats = crew(args.tier.lower(), args.files, [h for h in hints if h in PERSONA], plan)
    print("\n".join(" ".join(s) for s in seats) or "none")
