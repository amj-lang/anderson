#!/usr/bin/env python3
"""Pick the diff-review crew (the lens seats that join AGENT SMITH) from what the diff touches.

Deterministic on purpose: routing is pattern matching, not a model call.
usage: crew.py <tier> <file>...   (run from the repo root; files = the review scope)
prints one line per summoned lens: `<lens> <PERSONA> <model> <reason>`, or `none`.

ponytail: regex over paths + changed lines; over-summons on a name match (cheap: one extra
seat), under-summons security only below HARD (the tier forces SERAPH from HARD up).
"""
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


def crew(tier, files):
    hard = tier in ("hard", "critical")
    picks = {}
    for path in files:
        added, removed = changed(path)
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
    model = {"security": "opus", "performance": "opus" if hard else "sonnet", "leftovers": "sonnet"}
    return [(lens, PERSONA[lens], model[lens], why) for lens, why in picks.items()]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: crew.py <tier> <file>...")
    seats = crew(sys.argv[1].lower(), sys.argv[2:])
    print("\n".join(" ".join(s) for s in seats) or "none")
