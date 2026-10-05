#!/usr/bin/env python3
"""
⌐■-■  THE OPERATOR — anderson fleet monitor.

One terminal, every Claude Code session: repo · anderson task · persona (who is on the job)
· stage · model · what it is doing right now · $ · context · age. Runs OUTSIDE Claude
(plain python curses in a tmux pane, zero tokens). Sessions are the actors; this is the
Operator watching the screens.

    python3 bin/fleet.py               # live TUI (needs a TTY; best inside tmux)
    python3 bin/fleet.py --once        # one plain-text frame, for scripts / non-TTY
    python3 bin/fleet.py --demo        # add four synthetic sessions (try the UI, no Claude)
    python3 bin/fleet.py --selftest    # alignment invariant: every line == terminal width
    python3 bin/fleet.py --ascii       # single-byte glyphs (CJK locale / odd terminals)
    python3 bin/fleet.py --no-intro    # skip the digital-rain boot
    python3 bin/fleet.py --theme zion  # matrix · construct · zion · nebuchadnezzar · agent (saved)
    python3 bin/fleet.py --plain       # plain wording instead of Matrix lingo (saved; --lingo reverts)
    python3 bin/fleet.py --calm        # no motion in any theme (saved; --motion reverts)
    python3 bin/fleet.py --jack SID    # bring that session's terminal tab to the front (banner clicks run this)
    python3 bin/fleet.py --focus       # bring the running fleet's own tab back to the front

Data, richest first, each optional (the view degrades, never breaks):
  ~/.claude/fleet/<sid>.status.json   heartbeat from bin/heartbeat.py (statusline): $, ctx, model
  ~/.claude/fleet/<sid>.event.json    hooks/fleet_event.py: waiting-on-you vs working, and which task
  ~/.claude/projects/<cwd>/<sid>.jsonl transcript tail: last tool, last words, ctx tokens
  <repo>/feature-research/<task>/state.md  that session's stage/verdicts/iteration/tier -> persona
  ps + lsof + tmux                    sessions with no hooks at all, and the pane to jack into

Keys: ↑↓/jk tune · ⏎/1-9 jack in (revive, if dead; spawn, on a repo) · N new agent · w next ringing
      o read plan · r kill · b hide · h show hidden · space fold repos · m sound · / filter · ? manual · q
Prefs (theme, wording, motion, sound) persist in ~/.claude/fleet/prefs.json.
"""
import glob, json, os, random, re, shutil, signal, subprocess, sys, time, unicodedata

FLEET_DIR = os.path.expanduser(os.environ.get("ANDERSON_FLEET_DIR", "~/.claude/fleet"))
PROJECTS = os.path.expanduser("~/.claude/projects")
HERE = os.path.dirname(os.path.abspath(__file__))
STALE_S = 24 * 3600          # forget sessions with no sign of life for a day
CTX_WINDOW = 200_000         # fallback when the heartbeat has no context_window_size
REFRESH_S = 2.0
IDLE_S = 5 * 60              # a ring older than this stops pulsing and goes white: it still needs you, it just stopped shouting
FULL_REPAINT_S = 10.0        # erase + redraw the whole screen this often; the diff repaint cannot see what the terminal lost

# ──────────────────────────────────────────────────────────────────────── glyphs
UNI = dict(eyes="⌐■-■", cur="▸", ring="☎", dead="✝", loop="⟲", run="▶", ship="★", hid="◌",
           bar="▓", trk="░", rule="─", ell="…", det="▍", cursor="█",
           rain=("0·1 1", "1 0·1", " 1·10", "1·0 1"), raincol="01·10")
ASCII = dict(eyes="[-_-]", cur=">", ring="!", dead="x", loop="~", run=">", ship="*", hid="h",
             bar="#", trk=".", rule="-", ell="~", det="|", cursor="_",
             rain=("0.1 1", "1 0.1", " 1.10", "1.0 1"), raincol="01.10")
G = dict(UNI)

# stage -> (glyph key, persona, model/effort, quote mood)
PERSONA = {
    "plan":        ("arch",  "ARCHITECT",    "opus/medium",   "design"),
    "grill":       ("grill", "INTERROGATOR", "you",           "insight"),
    "plan_review": ("orac",  "ORACLE",       "opus/{pe}",     "insight"),
    "implement":   ("neo",   "NEO",          "sonnet/medium", "action"),
    "repair":      ("trin",  "TRINITY",      "opus/high",     "action"),
    "diff_review": ("smith", "AGENT SMITH",  "opus/{de}",     "adversary"),
    "done":        ("one",   "THE ONE",      "shipped",       "mentor"),
    "aborted":     ("smith", "AGENT SMITH",  "aborted",       "adversary"),
}
PGLYPH_UNI = dict(arch="▲", grill="◇", orac="◎", neo="●", trin="✚", smith="▣", one="★", none="○")
PGLYPH_ASCII = dict(arch="A", grill="?", orac="O", neo="N", trin="+", smith="S", one="*", none="o")
PGLYPH = dict(PGLYPH_UNI)


def use_ascii():
    G.clear(); G.update(ASCII); PGLYPH.clear(); PGLYPH.update(PGLYPH_ASCII)


def is_ascii():
    return G["eyes"] == ASCII["eyes"]      # G is mutated in place, so `G is ASCII` never holds


# ─────────────────────────────────────────────────────────── display-width text
def _cw(ch):
    o = ord(ch)
    if o < 32 or o == 0x7F or unicodedata.combining(ch):
        return 0
    if 0xFE00 <= o <= 0xFE0F or o == 0x200D or o == 0x200B:   # variation sel., ZWJ, ZWSP
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    if 0x1F300 <= o <= 0x1FAFF or 0x1F000 <= o <= 0x1F2FF:    # emoji planes render 2 cells
        return 2
    return 1


def dw(s):
    return sum(_cw(c) for c in s)


def fit(s, w, align="l"):
    """Exactly w cells: truncate with an ellipsis, then pad. Never overflows."""
    s = "" if s is None else str(s).replace("\n", " ").replace("\t", " ")
    if w <= 0:
        return ""
    if dw(s) > w:
        out, used = [], 0
        for ch in s:
            c = _cw(ch)
            if used + c > w - 1:
                break
            out.append(ch); used += c
        s = "".join(out) + G["ell"]
        s += " " * (w - dw(s))
    pad = w - dw(s)
    if align == "r":
        return " " * pad + s
    if align == "c":
        return " " * (pad // 2) + s + " " * (pad - pad // 2)
    return s + " " * pad


def rule(w):
    return G["rule"] * w


# ────────────────────────────────────────────────────────────── small helpers
def jload(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def alive(pid):
    if not pid:
        return None
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return None


def enc_cwd(cwd):
    return re.sub(r"[^A-Za-z0-9-]", "-", cwd or "")


def age_str(ts):
    if not ts:
        return "—" if not is_ascii() else "-"
    s = max(0, int(time.time() - ts))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


def field(text, key):
    m = re.search(rf"^\s*(?:[-*]\s+)?\**{re.escape(key)}\**\s*:\s*\**\s*(.*?)\s*\**\s*(?:#.*)?$",
                  text, re.M)
    return m.group(1).strip() if m else None


def repo_root(cwd):
    d = cwd or ""
    while d and d != "/":
        if os.path.isdir(os.path.join(d, "feature-research")) or _is_repo_dir(d):
            return d
        d = os.path.dirname(d)
    return cwd


def anderson_state(root, task=None, guess=True):
    """The session's OWN state.md, parsed leniently. `task` comes from the hook, which sees which
    task dir this session writes. guess=False (the hook is wired but this session has touched no
    task) means no task: guessing the newest state.md under root is what made every session in a
    shared checkout wear the same task, persona and stage. Only a hookless session still guesses."""
    if not root:
        return {}
    if task:
        own = os.path.join(root, "feature-research", task, "state.md")
        paths = [own] if os.path.exists(own) else []
    elif guess:
        paths = glob.glob(os.path.join(root, "feature-research", "*", "state.md"))
    else:
        paths = []
    if not paths:
        return {}
    p = max(paths, key=lambda x: os.path.getmtime(x))
    try:
        t = open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return {}
    st = {k: field(t, k) for k in
          ("task", "stage", "iteration", "max_iterations", "plan_verdict", "diff_verdict", "branch", "gate", "tier")}
    st["task"] = st["task"] or os.path.basename(os.path.dirname(p))
    st["mtime"] = os.path.getmtime(p)
    return st


# ─────────────────────────────────────────────────────────── transcript tail
def _tool_summary(name, inp):
    inp = inp or {}
    if name == "Bash":
        return (inp.get("command") or "").strip().split("\n")[0]
    if name in ("Read", "Edit", "Write", "MultiEdit", "NotebookEdit"):
        return os.path.basename(inp.get("file_path") or inp.get("notebook_path") or "")
    if name == "Agent":
        return inp.get("subagent_type") or inp.get("description") or ""
    if name in ("Grep", "Glob"):
        return inp.get("pattern") or ""
    if name == "Skill":
        return inp.get("skill") or ""
    return ""


def subagents(transcript_path, now=None):
    """Subagents this session spawned: (total, running, last), read from the transcript's sibling
    directory (same name minus .jsonl) /subagents/agent-*.jsonl and their .meta.json.
    ponytail: 'running' = transcript touched in the last 20 s; good enough without parsing every file."""
    if not transcript_path:
        return (0, 0, "")
    now = now or time.time()
    d = os.path.join(os.path.dirname(transcript_path), os.path.basename(transcript_path)[:-6], "subagents")
    files = sorted(glob.glob(os.path.join(d, "agent-*.jsonl")), key=os.path.getmtime)
    if not files:
        return (0, 0, "")
    running = sum(1 for f in files if now - os.path.getmtime(f) < 20)
    meta = jload(files[-1][:-6] + ".meta.json") or {}
    last = meta.get("agentType") or ""
    if meta.get("description"):
        last += f' "{meta["description"]}"'
    if meta.get("model"):
        last += f" ({meta['model']})"
    return (len(files), running, last.strip())


def read_transcript(path, tail_bytes=262144):
    """Tail-parse a session .jsonl -> dict(state, tool, tool_arg, text, ctx_tokens, model, ts, start)."""
    out = dict(state=None, tool=None, tool_arg="", text="", ctx_tokens=None, model=None, ts=None, start=None,
               title="", branch=None, start_cwd=None)
    if not path or not os.path.isfile(path):
        return out
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(0)
            head = f.read(65536).decode("utf-8", "replace").split("\n")
            f.seek(max(0, size - tail_bytes))
            tail = f.read().decode("utf-8", "replace").split("\n")
    except Exception:
        return out
    for ln in head:
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if d.get("timestamp") and not out["start"]:
            out["start"] = _iso(d["timestamp"])
        if d.get("cwd") and not out["start_cwd"]:
            out["start_cwd"] = d["cwd"]                       # where claude was launched: the tab's directory
        if d.get("type") == "summary" and d.get("summary") and not out["title"]:
            out["title"] = str(d["summary"]).strip()          # /resume title, when Claude Code wrote one
        if d.get("type") == "user" and not d.get("isSidechain") and not d.get("isMeta") and not out["title"]:
            c = (d.get("message") or {}).get("content")
            txt = c if isinstance(c, str) else " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text") if isinstance(c, list) else ""
            txt = txt.strip()
            if txt and not txt.startswith("<"):               # skip slash-command / caveat wrappers
                out["title"] = txt.split("\n")[0][:120]
        if out["start"] and out["title"] and out["start_cwd"]:
            break
    recs = []
    for ln in reversed(tail[1:] if size > tail_bytes else tail):
        if not ln.strip():
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if d.get("type") in ("assistant", "user"):
            recs.append(d)
        if len(recs) >= 40:
            break
    if not recs:
        return out
    last = recs[0]
    out["ts"] = _iso(last.get("timestamp"))
    out["branch"] = last.get("gitBranch") or None
    main = [r for r in recs if not r.get("isSidechain")]
    side_active = bool(last.get("isSidechain"))
    for r in main:                                   # newest main-chain assistant: usage, model, tools
        if r.get("type") == "assistant":
            msg = r.get("message") or {}
            u = msg.get("usage") or {}
            out["ctx_tokens"] = sum(int(u.get(k) or 0) for k in
                                    ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")) or None
            out["model"] = msg.get("model")
            break
    for r in main:                                   # last words, for the detail pane
        if r.get("type") == "assistant":
            for b in (r.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                    out["text"] = b["text"].strip().split("\n")[0]
                    break
            if out["text"]:
                break
    head_main = main[0] if main else last
    content = (head_main.get("message") or {}).get("content")
    tools = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"] \
        if isinstance(content, list) else []
    if head_main.get("type") == "assistant" and tools:
        t = tools[-1]
        out["tool"], out["tool_arg"] = t.get("name"), _tool_summary(t.get("name"), t.get("input"))
        out["state"] = "tool"                        # tool issued, no result yet: running or permission
    elif head_main.get("type") == "assistant":
        out["state"] = "idle"                        # turn ended with words: waiting on the human
    else:
        out["state"] = "think"                       # prompt or tool_result in, model working
    if side_active:
        out["state"] = "tool"
        if out["tool"] != "Agent":
            out["tool"], out["tool_arg"] = "Agent", out["tool_arg"] or "subagent"
    return out


def _iso(s):
    if not s:
        return None
    try:
        from datetime import datetime, timezone
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────── discovery
def _ps():
    """[(pid, ppid, command)] or [] when ps is unavailable (sandboxes, Windows)."""
    try:
        r = subprocess.run(["ps", "-eo", "pid,ppid,command"], capture_output=True, text=True, timeout=3)
    except Exception:
        return []
    rows = []
    for ln in r.stdout.splitlines()[1:]:
        p = ln.strip().split(None, 2)
        if len(p) == 3 and p[0].isdigit():
            rows.append((int(p[0]), int(p[1]), p[2]))
    return rows


def _is_claude(cmd):
    head = cmd.split()[:2]
    if not head:
        return False
    a0 = os.path.basename(head[0])
    if a0 == "claude":
        return True
    return any("claude-code" in h or h.endswith("/claude") for h in head)


def _under_claude(pid, parents, claude_pids):
    """True when an ancestor of `pid` is itself a claude process (headless child run, not a session)."""
    p = parents.get(pid)
    for _ in range(12):
        if not p or p <= 1:
            return False
        if p in claude_pids:
            return True
        p = parents.get(p)
    return False


def _cwd_of(pid):
    try:
        r = subprocess.run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
                           capture_output=True, text=True, timeout=3)
        for ln in r.stdout.splitlines():
            if ln.startswith("n"):
                return ln[1:]
    except Exception:
        pass
    return None


def _tmux_panes():
    """{pane_pid: (pane_id, 'session:win.pane')} for every tmux pane, {} without tmux."""
    try:
        r = subprocess.run(["tmux", "list-panes", "-a", "-F", "#{pane_pid} #{pane_id} #{session_name}:#{window_index}.#{pane_index}"],
                           capture_output=True, text=True, timeout=3)
    except Exception:
        return {}
    out = {}
    for ln in r.stdout.splitlines():
        p = ln.split()
        if len(p) == 3 and p[0].isdigit():
            out[int(p[0])] = (p[1], p[2])
    return out


def _pane_for(pid, parents, panes):
    seen = 0
    while pid and pid in parents and seen < 32:
        if pid in panes:
            return panes[pid]
        pid = parents[pid]; seen += 1
    return (None, None)


def dismiss(sid, clean=False):
    """Hide a session from the list for good (~/.claude/fleet/dismissed). clean=True also removes its
    heartbeat/event files, for rows whose process is gone."""
    try:
        os.makedirs(FLEET_DIR, exist_ok=True)
        with open(os.path.join(FLEET_DIR, "dismissed"), "a") as f:
            f.write(sid + "\n")
        if clean:
            for f in glob.glob(os.path.join(FLEET_DIR, sid + ".*.json")):
                os.remove(f)
    except Exception:
        pass


def unhide(sid):
    """Take a session off the dismissed list."""
    path = os.path.join(FLEET_DIR, "dismissed")
    try:
        keep = [x for x in open(path).read().split() if x != sid]
        with open(path, "w") as f:
            f.write("".join(x + "\n" for x in keep))
    except Exception:
        pass


SHOW_HIDDEN = False   # `h`: list the dismissed rows too (flagged ◌, dim); `b` on one of them un-hides it


def discover(include_ps=True, hidden=None):
    """Merge heartbeat, hook events, ps discovery and transcripts into session dicts.
    hidden=True lists dismissed sessions too, each with row["hidden"] set."""
    hidden = SHOW_HIDDEN if hidden is None else hidden
    now = time.time()
    sess = {}
    dismissed = set()
    try:
        dismissed = set(open(os.path.join(FLEET_DIR, "dismissed")).read().split())
    except Exception:
        pass
    for p in glob.glob(os.path.join(FLEET_DIR, "*.status.json")) + glob.glob(os.path.join(FLEET_DIR, "*.event.json")):
        d = jload(p)
        if not d or not d.get("session_id"):
            continue
        s = sess.setdefault(d["session_id"], {"sid": d["session_id"], "src": set()})
        kind = "status" if p.endswith(".status.json") else "event"
        s["src"].add(kind)
        for k in ("cwd", "transcript_path", "tmux_pane", "pid"):
            if d.get(k) and not (k == "pid" and int(d[k]) <= 1):   # pid 1 = orphaned emitter, unknown
                s.setdefault(k, d[k])
        if kind == "status":
            s.update({k: d.get(k) for k in ("model", "cost_usd", "duration_ms", "lines_added",
                                            "lines_removed", "ctx_pct", "ctx_tokens")})
            s["hb_ts"] = d.get("ts")
        else:
            s["ev"] = d
    ps = _ps() if include_ps else []
    parents = {pid: ppid for pid, ppid, _ in ps}
    claude_pids = {pid for pid, _, cmd in ps if _is_claude(cmd)}
    # a session whose process descends from another claude is that session's machinery (the bg
    # daemon's spare / pty-host, a `claude -p` review run): its hooks and heartbeat fire too, but it is not a row
    for sid in [k for k, v in sess.items() if v.get("pid") and _under_claude(v["pid"], parents, claude_pids)]:
        del sess[sid]
    panes = _tmux_panes() if ps else {}
    # one process, several session ids (/clear, /resume): only the freshest one is that process now
    by_pid = {}
    for s in sess.values():
        if s.get("pid"):
            by_pid.setdefault(s["pid"], []).append(s)
    for group in by_pid.values():
        group.sort(key=lambda o: -(o.get("hb_ts") or (o.get("ev") or {}).get("ts") or 0))
        for stale in group[1:]:
            del sess[stale["sid"]]
    known_pids = {s.get("pid") for s in sess.values()}
    claimed = {s.get("transcript_path") for s in sess.values()}
    orphans = [s for s in sess.values() if not s.get("pid") and s.get("cwd")]
    for pid, _, cmd in ps:
        if pid == os.getpid() or not _is_claude(cmd) or pid in known_pids:
            continue
        if _under_claude(pid, parents, claude_pids):   # `claude -p` spawned by a session (reviewers, hooks): not a row
            continue
        cwd = _cwd_of(pid)
        if not cwd:
            continue
        # a heartbeat/hook session with no usable pid in this cwd: this is its process, not a new row
        mine = [o for o in orphans if o["cwd"] == cwd]
        if mine:
            o = min(mine, key=lambda o: -(o.get("hb_ts") or (o.get("ev") or {}).get("ts") or 0))
            o["pid"] = pid; orphans.remove(o); known_pids.add(pid)
            continue
        cands = sorted(glob.glob(os.path.join(PROJECTS, enc_cwd(cwd), "*.jsonl")),
                       key=os.path.getmtime, reverse=True)
        cands = [c for c in cands if c not in claimed and now - os.path.getmtime(c) < STALE_S]
        tp = cands[0] if cands else None
        sid = os.path.basename(tp)[:-6] if tp else f"pid:{pid}"
        if tp:
            claimed.add(tp)
        sess[sid] = {"sid": sid, "src": {"ps"}, "cwd": cwd, "pid": pid, "transcript_path": tp}
    for o in orphans:                 # still no process after adoption, and ps could see processes: gone
        if ps:
            o["no_proc"] = True
    for s in sess.values():
        if s.get("pid") and not s.get("tmux_pane") and ps:
            s["tmux_pane"], s["tmux_addr"] = _pane_for(s["pid"], parents, panes)
    rows = []
    for s in sess.values():
        if s["sid"] in dismissed and not hidden:
            continue
        r = enrich(s, now)
        if r is not None:
            r["hidden"] = s["sid"] in dismissed
            rows.append(r)
    rows.sort(key=lambda r: (r["hidden"], {"ring": 0, "work": 1, "sentinel": 2}.get(r["status"], 1), r["repo"], r["task"]))
    return rows


WAITING_TOOLS = ("AskUserQuestion", "ExitPlanMode")   # a tool call that is itself a question to you
STUCK_S = 15 * 60          # a turn silent this long with no Stop (Esc interrupt) is waiting on you
GUESS_S = 30               # hookless sessions: "turn ended" only after the transcript sat this long


def row_status(ev, tr, dead, now):
    """(status, now text, ring start ts). The hook event is the truth when there is one: Stop and
    Notification mean "waiting on you", prompt and tool events mean "working". The transcript only
    adds what no hook reports: a tool call that is itself a question, and a turn interrupted with Esc
    (no Stop fires) that has sat silent for STUCK_S. And a waiting event is stale once the transcript
    shows the session working after it (a Stop the scheduler blocked, on a session whose hooks.json
    predates the PreToolUse hook). Guessing "turn ended" off the transcript while
    hooks exist is what rang on every mid-turn "Now let me check X" line."""
    tool, arg = tr.get("tool"), tr.get("tool_arg") or ""
    state, ts = tr.get("state"), tr.get("ts")

    def ring(label, since):
        return "ring", f"{G['ring']} {label}" + (f" {age_str(since)}" if since else ""), since

    if dead:
        return "sentinel", f"{G['dead']} sentinel", None
    moved_on = state in ("tool", "think") and ts and ts > (ev.get("ts") or 0) + 1
    if ev.get("waiting") and not moved_on:   # a Stop another hook blocked: the session carried on
        perm = "permission" in str(ev.get("notification") or "").lower()
        return ring(f"permission {tool or ''}".rstrip() if perm else "ring", ev.get("since") or ev.get("ts"))
    if ev.get("event") == "SessionStart":
        return "work", f"{G['run']} jacked in", None
    if not ev and state == "idle" and ts and now - ts > GUESS_S:
        return ring("ring", ts)
    if state == "tool" and tool in WAITING_TOOLS:
        return ring("question", ts)
    if state in ("think", "idle") and ts and now - ts > STUCK_S:
        return ring("idle", ts)
    if state == "tool":
        return "work", f"{G['run']} {tool} {arg}".rstrip(), None
    return "work", f"{G['run']} thinking", None


def enrich(s, now):
    tr = read_transcript(s.get("transcript_path"))
    if not s.get("transcript_path") and s.get("cwd") and s.get("sid") and not s["sid"].startswith("pid:"):
        s["transcript_path"] = os.path.join(PROJECTS, enc_cwd(s["cwd"]), s["sid"] + ".jsonl")
        tr = read_transcript(s["transcript_path"])
    ev = s.get("ev") or {}
    last_seen = max([x for x in (s.get("hb_ts"), ev.get("ts"), tr.get("ts")) if x] or [0])
    if now - last_seen > STALE_S and not alive(s.get("pid")):
        return None
    root = repo_root(s.get("cwd"))
    st = anderson_state(root, ev.get("task"), guess=not ev)
    stage = (st.get("stage") or "").lower()
    if stage in ("ship",):
        stage = "done"
    gk, persona, model_spec, mood = PERSONA.get(stage, ("none", "T. ANDERSON", "", ""))
    model_spec = model_spec.format(**review_effort(st.get("tier")))
    if not model_spec:
        model_spec = _short_model(s.get("model") or tr.get("model") or "")
    pid_alive = alive(s.get("pid"))
    dead = ev.get("ended") or pid_alive is False or s.get("no_proc", False)
    status, now_txt, since = row_status(ev, tr, dead, now)
    it, mx = st.get("iteration"), st.get("max_iterations")
    ctx_pct = s.get("ctx_pct")
    toks = s.get("ctx_tokens") or tr.get("ctx_tokens")
    if ctx_pct is None and toks:
        win = CTX_WINDOW if toks <= CTX_WINDOW else 1_000_000   # ponytail: >200k tokens => 1M-window model
        ctx_pct = min(100.0, 100.0 * toks / win)
    start = tr.get("start") or (now - (s.get("duration_ms") or 0) / 1000.0 if s.get("duration_ms") else None)
    return {
        "sid": s["sid"], "pid": s.get("pid"), "cwd": s.get("cwd") or "", "root": root,
        "repo": os.path.basename(root or s.get("cwd") or "") or "?",
        "task": st.get("task") or "", "title": tr.get("title") or "", "stage": stage, "persona": persona, "pglyph": PGLYPH[gk],
        "mood": mood, "model": model_spec, "iteration": it, "max_iter": mx,
        "plan_verdict": st.get("plan_verdict"), "diff_verdict": st.get("diff_verdict"), "branch": git_branch(root) or st.get("branch") or tr.get("branch"),
        "gate": (st.get("gate") or "").lower(), "tier": (st.get("tier") or "").lower(),
        "dejavu": bool(it and it.isdigit() and int(it) > 0),
        "status": status, "now": now_txt, "text": tr.get("text") or "",
        "cost": s.get("cost_usd"), "ctx_pct": ctx_pct, "ctx_tokens": toks,
        "lines": (s.get("lines_added"), s.get("lines_removed")),
        "start": start, "last_seen": last_seen, "agents": subagents(s.get("transcript_path"), now),
        "idle": status == "ring" and bool(since) and now - since > IDLE_S, "since": since,
        "start_cwd": tr.get("start_cwd"),
        "transcript_path": s.get("transcript_path"),
        "tmux_pane": s.get("tmux_pane"), "tmux_addr": s.get("tmux_addr"),
        "shipped": stage == "done", "hb_ts": s.get("hb_ts"),
    }


def review_effort(tier):
    """Tier -> review effort (docs/tiering.md): plan-review xhigh only at critical, diff-review from hard."""
    t = (tier or "").lower()
    return {"pe": "xhigh" if t == "critical" else "high", "de": "xhigh" if t in ("hard", "critical") else "high"}


def _short_model(m):
    m = (m or "").lower().replace("claude-", "")
    for k in ("fable", "opus", "sonnet", "haiku"):
        if k in m:
            return k
    return m[:12]


# ── workspace: the repos under the launch directory, where N spawns ──────────────────
WS_SCAN_TTL = 30           # ponytail: a repo cloned mid-run appears within this ceiling, not instantly
_WS_CACHE = {}             # ws abs path -> (scanned_at, [{name, path, kind, repos?}])


def workspace_root(cwd):
    """The workspace a repo sits in: repo_root(cwd)'s parent when it is a real repo, else cwd
    itself (no repo found -> today's flat list, criterion 7)."""
    cwd = cwd or os.getcwd()
    r = repo_root(cwd)
    if r and _is_repo_dir(r):
        return os.path.dirname(r)
    return cwd


def _is_repo_dir(p):
    # a git worktree or submodule checkout has `.git` as a FILE, not a dir -- exists(), not isdir(),
    # or every worktree sitting in the workspace is invisible to the scan and to repo_root()
    return os.path.exists(os.path.join(p, ".git"))


def _gitdir(p):
    """The git dir of the checkout at `p`: `.git` itself, or where a `.git` file points. None outside git."""
    g = os.path.join(p or "", ".git")
    if os.path.isdir(g):
        return g
    try:
        with open(g) as f:
            m = re.match(r"gitdir:\s*(.+?)\s*$", f.read())
    except OSError:
        return None
    return os.path.normpath(os.path.join(p, m.group(1))) if m else None


def worktree_main(p):
    """The main checkout a linked worktree belongs to, None when `p` is not one. Any location
    counts (.worktrees/, .claude/worktrees/, a sibling dir): its git dir is <main>/.git/worktrees/<x>.
    Submodules also carry a `.git` file (-> .git/modules/), and stay repos of their own."""
    g = _gitdir(p)
    m = re.match(r"(.+)/\.git/worktrees/[^/]+$", g or "")
    return os.path.realpath(m.group(1)) if m else None


def git_branch(p):
    """The branch checked out at `p` right now (HEAD read off disk, no subprocess). The transcript's
    gitBranch is where the session started, which a worktree or a checkout since has made stale."""
    g = _gitdir(p)
    try:
        with open(os.path.join(g, "HEAD")) as f:
            head = f.read().strip()
    except (OSError, TypeError):
        return None
    return head[len("ref: refs/heads/"):] if head.startswith("ref: refs/heads/") else None


def scan_workspace(ws):
    """The repos under `ws`, flat: [{name, path}]. A direct child repo is `name`; repos one or two
    levels inside a plain dir are `dir/name` (`dir/sub/name`). os.scandir only, no git subprocess;
    linked worktrees are skipped (their sessions row under the main checkout). Memoised
    WS_SCAN_TTL seconds per workspace."""
    now = time.time()
    cached = _WS_CACHE.get(ws)
    if cached and now - cached[0] < WS_SCAN_TTL:
        return cached[1]
    out = []

    def walk(path, prefix, depth):
        try:
            entries = sorted(os.scandir(path), key=lambda e: e.name)
        except Exception:
            return
        for e in entries:
            try:
                if e.name.startswith(".") or not e.is_dir(follow_symlinks=False) or worktree_main(e.path):
                    continue
                if _is_repo_dir(e.path):
                    out.append({"name": prefix + e.name, "path": e.path})
                elif depth < 2:
                    walk(e.path, f"{prefix}{e.name}/", depth + 1)
            except Exception:
                continue

    if ws:
        walk(ws, "", 0)
    _WS_CACHE[ws] = (now, out)
    return out


# every key a session row carries (enrich()'s return dict), so cell()/detail_card()/render()
# never half-miss one on a synthetic repo/section row
_WS_BASE = dict(
    pid=None, cwd="", root="", task="", title="", stage="", persona="", pglyph="", mood="", model="",
    iteration=None, max_iter=None, plan_verdict=None, diff_verdict=None, branch=None, gate="", tier="",
    dejavu=False, text="", cost=None, ctx_pct=None, ctx_tokens=None, lines=(None, None),
    start=None, last_seen=None, agents=(0, 0, ""), idle=False, transcript_path=None, since=None,
    start_cwd=None, tmux_pane=None, tmux_addr=None, shipped=False, hb_ts=None, hidden=False, status="work",
)


def session_root(s):
    """The repo a session belongs to. A session in a linked worktree (fleet's `.worktrees/`, Claude
    Code's `.claude/worktrees/`, a sibling dir) counts under the repo it came from."""
    rp = os.path.realpath(s.get("root") or s.get("cwd") or "")
    return worktree_main(rp) or rp


def repo_target(path, name=None):
    """A repo row for `path`: what N spawns into."""
    return {**_WS_BASE, "sid": f"repo:{path}", "kind": "repo", "repo": name or os.path.basename(path),
            "path": path, "root": path, "cwd": path, "now": ""}


def hides(h, name):
    """Hidden entry `h` covers repo `name`: itself, a dir above it, or `x` saved by the old tree
    (relative to its group) for `group/x`."""
    return name == h or name.startswith(h + "/") or name.endswith("/" + h)


def ws_rows(sessions, ws, filt="", folded=False, hidden=(), show_hidden=False):
    """Two sections: every live session (discover()'s order, ringing first), then the workspace's
    repos, the places N spawns a new agent. `hidden` names repos dismissed with `b`: left out of
    the repos section until show_hidden. folded: the repos section is one header line."""
    fl = (filt or "").lower()
    out = [s for s in sessions if not fl or fl in (s.get("repo", "") + " " + s.get("task", "") + " " + s.get("title", "")).lower()]
    hid = lambda name: any(hides(h, name) for h in hidden)
    repos = [r for r in scan_workspace(ws) if show_hidden or not hid(r["name"])]
    repos = [r for r in repos if not fl or fl in r["name"].lower()]
    if not repos:
        return out
    live = {}
    for s in sessions:
        if s.get("status") != "sentinel":
            live[session_root(s)] = live.get(session_root(s), 0) + 1
    out.append({**_WS_BASE, "sid": "section:repos", "kind": "section", "repo": f"repos ({len(repos)})",
                "collapsed": folded, "now": f"{'enter' if is_ascii() else '⏎'} or N on a repo spawns an agent there · space folds"})
    if not folded:
        for r in repos:
            row = repo_target(r["path"], r["name"])
            n = live.get(os.path.realpath(r["path"]), 0)
            row["now"] = f"{n} agent{'s' if n != 1 else ''}" if n else ""
            row["hidden"] = hid(r["name"])
            out.append(row)
    return out


# ───────────────────────────────────────────────────────────────────── demo
def demo_rows():
    now = time.time()
    base = dict(pid=None, cwd="", root="", plan_verdict="ship", diff_verdict="pending", lines=(212, 48),
                tmux_pane=None, tmux_addr=None, shipped=False, hb_ts=now, last_seen=now, sid="demo")
    mk = lambda **k: {**base, **k}
    st = lambda s: PERSONA[s]
    return [
        mk(sid="demo-1", repo="fashion-webapp-2", task="ar-2270-sku-images-lightbox", stage="diff_review",
           persona=st("diff_review")[1], pglyph=PGLYPH["smith"], mood="adversary", model="opus/xhigh",
           iteration="1", max_iter="2", dejavu=True, status="ring", now=f"{G['ring']} ring",
           text="47 passed, 0 failed. Verdict: fix_first, one unproven criterion.", cost=1.42, ctx_pct=61,
           start=now - 12 * 60, diff_verdict="fix_first", tier="hard"),
        mk(sid="demo-2", repo="ai-shoot-service", task="remove-db-triggers", stage="implement",
           persona=st("implement")[1], pglyph=PGLYPH["neo"], mood="action", model="sonnet/medium",
           iteration="0", max_iter="2", dejavu=False, status="work", now=f"{G['run']} Edit orders.py",
           text="Replacing the trigger with an explicit write in process_order().", cost=0.88, ctx_pct=34,
           start=now - 4 * 60, tier="normal"),
        mk(sid="demo-3", repo="claude-loop", task="readbility", stage="grill",
           persona=st("grill")[1], pglyph=PGLYPH["grill"], mood="insight", model="you",
           iteration="0", max_iter="2", dejavu=False, status="ring", now=f"{G['ring']} ring",
           text="Question 3 of 7: should the What block cap at three lines or three sentences?", cost=0.12,
           ctx_pct=9, start=now - 41 * 60, tier="trivial"),
        mk(sid="demo-4", repo="fashion-webapp-2", task="sku-bulk-upload", stage="plan",
           persona=st("plan")[1], pglyph=PGLYPH["arch"], mood="design", model="opus/medium",
           iteration="2", max_iter="2", dejavu=True, status="sentinel", now=f"{G['dead']} sentinel",
           text="", cost=0.31, ctx_pct=None, start=now - 2 * 3600, pid=None, tier="critical"),
    ]


# ────────────────────────────────────────────────────────────────── themes
# Five looks. `t` cycles them live; --theme <name> sets one; the choice persists in
# ~/.claude/fleet/theme. Motion is opt-in per theme: rain = header tail, pulse = ringing rows
# breathe (1/s), spin = a quiet spinner in the header. --calm turns all motion off.
THEMES = {
    "matrix":   dict(desc="green phosphor, header rain, rings breathe",
                     hdr="green", accent="green", ring="green", dead="dim", bar="green", quote="green",
                     rain=True, pulse=True, spin=False, eggs="full"),
    "construct": dict(desc="white void, no motion, quotes only",
                     hdr="white", accent="white", ring="white", dead="dim", bar="white", quote="dim",
                     rain=False, pulse=False, spin=False, eggs="quiet"),
    "zion":     dict(desc="amber machine level, slow spinner",
                     hdr="amber", accent="amber", ring="yellow", dead="dim", bar="amber", quote="amber",
                     rain=False, pulse=False, spin=True, eggs="full"),
    "nebuchadnezzar": dict(desc="cold blue ship console, heartbeat dot",
                     hdr="cyan", accent="blue", ring="cyan", dead="dim", bar="blue", quote="cyan",
                     rain=False, pulse=True, spin=False, eggs="full"),
    "agent":    dict(desc="monochrome suit, red alerts, adversary lines",
                     hdr="white", accent="dim", ring="red", dead="dim", bar="white", quote="red",
                     rain=False, pulse=False, spin=False, eggs="smith"),
}
THEME_ORDER = list(THEMES)
THEME = dict(THEMES["matrix"], name="matrix")
PREFS_FILE = os.path.join(FLEET_DIR, "prefs.json")   # {theme, plain, calm}: chosen once, kept
SPIN = "◐◓◑◒"
PLAIN = False        # wording: False = Matrix lingo (zion / jacked in / ringing / sentinel), True = plain


def set_theme(name, calm=False):
    global THEME
    name = name if name in THEMES else "matrix"
    THEME = dict(THEMES[name], name=name)
    if calm:
        THEME.update(rain=False, pulse=False, spin=False)
    return THEME


def load_prefs():
    d = jload(PREFS_FILE) or {}
    ws = d.get("workspaces")
    return {"theme": d.get("theme") or "matrix", "plain": bool(d.get("plain")), "calm": bool(d.get("calm")),
            "cost": bool(d.get("cost")), "notify": bool(d.get("notify")),
            "sound": bool(d.get("sound")), "ring": d.get("ring") or "phone",
            "workspaces": ws if isinstance(ws, dict) else {}}


def save_prefs(**kw):
    d = load_prefs(); d.update({k: v for k, v in kw.items() if v is not None})
    try:
        os.makedirs(FLEET_DIR, exist_ok=True)
        with open(PREFS_FILE, "w") as f:
            json.dump(d, f)
    except Exception:
        pass
    return d


def ws_prefs(ws):
    """Saved {hidden, folded} for this workspace; a malformed entry reads as empty, never crashes."""
    v = (load_prefs()["workspaces"] or {}).get(ws)
    v = v if isinstance(v, dict) else {}
    return {"hidden": list(v.get("hidden") or []), "folded": bool(v.get("folded"))}


def save_ws_prefs(ws, **kw):
    d = load_prefs()
    workspaces = dict(d["workspaces"])
    cur = dict(workspaces.get(ws) if isinstance(workspaces.get(ws), dict) else {})
    cur.update({k: v for k, v in kw.items() if v is not None})
    workspaces[ws] = cur
    save_prefs(workspaces=workspaces)
    return cur


def words(key):
    """Header/footer vocabulary; PLAIN swaps the Matrix lingo for plain English."""
    lingo = {
        "fleet": ("zion", "fleet"), "live": ("jacked in", "live"), "ring": ("ringing", "waiting"),
        "dead": ("sentinel", "dead"), "deads": ("sentinels", "dead"),
        "empty": ("There is no spoon.   /anderson:start to bend one.", "No sessions.   /anderson:start to begin."),
    }
    a, b = lingo[key]
    return b if PLAIN else a


# ────────────────────────────────────────────────────────────────── quotes
def load_quotes():
    q = {}
    try:
        for ln in open(os.path.join(HERE, "quotes.txt"), encoding="utf-8"):
            if "|" in ln:
                mood, txt = ln.rstrip("\n").split("|", 1)
                q.setdefault(mood.strip().lower(), []).append(txt.strip())
    except Exception:
        pass
    return q


QUOTES = load_quotes()

# boot lines: one per launch, in order, so every start greets you differently.
BOOT_LINES = [
    "Wake up, Neo…",
    "The Matrix has you.",
    "Follow the white rabbit.",
    "Knock, knock, Neo.",
    "There is no spoon.",
    "I know kung fu.",
    "Welcome to the real world.",
    "Free your mind.",
    "Mr. Anderson…",
    "Never send a human to do a machine's job.",
    "Dodge this.",
    "Choice. The problem is choice.",
    "He is beginning to believe.",
    "I can only show you the door.",
    "Everything that has a beginning has an end.",
    "the agents review the agents",
    "green is not understood — read what you merged",
]


def boot_line():
    """Rotate through BOOT_LINES across launches (counter in ~/.claude/fleet/boot_n)."""
    p = os.path.join(FLEET_DIR, "boot_n")
    try:
        n = int(open(p).read().strip() or 0)
    except Exception:
        n = 0
    try:
        os.makedirs(FLEET_DIR, exist_ok=True)
        open(p, "w").write(str(n + 1))
    except Exception:
        pass
    return BOOT_LINES[n % len(BOOT_LINES)]


def quote_for(row, t=None):
    t = time.time() if t is None else t
    if THEME.get("eggs") == "quiet":
        return ""
    if row.get("stage") == "diff_review" and row.get("diff_verdict") == "fix_first" and THEME.get("eggs") != "quiet":
        return "Mr. Anderson… did you think that test would pass?"
    mood = "adversary" if THEME.get("eggs") == "smith" else (row.get("mood") or "")
    pool = QUOTES.get(mood, []) or [x for v in QUOTES.values() for x in v]
    if not pool:
        return ""
    return pool[int(t // 30 + hash(row.get("sid", "")) % 7) % len(pool)]


# ──────────────────────────────────────────────────────────────── rendering
COLS = [  # key, title, width (None = elastic), align, min terminal width to show
    ("flag",    "",        2,    "l", 0),
    ("repo",    "repo",    None, "l", 0),
    ("task",    "task",    None, "l", 0),
    ("persona", "persona", 14,   "l", 0),
    ("stage",   "stage",   15,   "l", 0),
    ("tier",    "tier",    8,    "l", 110),
    ("model",   "model",   13,   "l", 140),
    ("now",     "now",     22,   "l", 85),
    ("cost",    "api$",    6,    "r", 100),
    ("ctx",     "ctx",     15,   "l", 120),
    ("ctxp",    "ctx",     4,    "r", 0),      # compact ctx, only when the bar is hidden
    ("age",     "age",     4,    "r", 100),
]
PREFIX = 3   # margin + cursor + space


SHOW_COST = False    # api$ column: on for API-key users (no limits), opt-in on subscriptions (--cost)


def layout(width):
    cols = [c for c in COLS if width >= c[4]]
    if not SHOW_COST and usage_limits():
        cols = [c for c in cols if c[0] != "cost"]
    if any(c[0] == "ctx" for c in cols):
        cols = [c for c in cols if c[0] != "ctxp"]
    fixed = sum(c[2] for c in cols if c[2]) + 2 * (len(cols) - 1) + PREFIX
    free = width - fixed
    while free < 20 and len(cols) > 4:                 # too narrow: shed from the right
        drop = [c for c in cols if c[0] not in ("flag", "repo", "task", "persona", "stage")]
        if not drop:
            break
        cols.remove(drop[-1])
        fixed = sum(c[2] for c in cols if c[2]) + 2 * (len(cols) - 1) + PREFIX
        free = width - fixed
    free = max(free, 4)
    rw = max(2, min(28, int(free * 0.4))); tw = max(2, min(56, free - rw))   # caps: wide terminals stay readable
    return [(k, t, (rw if k == "repo" else tw if k == "task" else w), a) for k, t, w, a, _ in cols]


HOT_CTX = 80     # % of context past which the ctx cell paints red: /compact before the next review


def ctx_span(width):
    """(x, cells) of the ctx column at this width, or None when it is hidden."""
    x = PREFIX
    for k, _, w, _ in layout(max(40, width)):
        if k in ("ctx", "ctxp"):
            return x, w
        x += w + 2
    return None


def hot_rows(rows):
    """sids whose context is past HOT_CTX and that are still alive: the ones to /compact."""
    return {r["sid"] for r in rows
            if r.get("ctx_pct") is not None and r["ctx_pct"] >= HOT_CTX and r["status"] != "sentinel"}


def cell_index(line, x):
    """Character index in `line` where display column x starts (wide chars aware)."""
    used = 0
    for i, ch in enumerate(line):
        if used >= x:
            return i
        used += _cw(ch)
    return len(line)


def ctx_bar(pct, w=10):
    if pct is None:
        return G["trk"] * w + "   " + ("—" if not is_ascii() else "-").rjust(1)
    n = max(0, min(w, int(round(pct / 100.0 * w))))
    return G["bar"] * n + G["trk"] * (w - n) + f" {int(pct):3d}%"


# how hard the pipeline decided this task is (state.md `tier`). Upper-case for the two that cost
# real review effort, so a screen of rows shows at a glance who is grinding.
TIER_LABEL = {"trivial": "triv", "normal": "normal", "hard": "HARD", "critical": "CRITICAL", "pending": "…"}


def cell(row, key, frame):
    if row.get("kind") == "section":
        if key == "repo":
            mark = ">v" if is_ascii() else "▸▾"
            return f"{mark[0] if row.get('collapsed') else mark[1]} {row['repo']}"
        return row["now"] if key == "task" else ""
    if row.get("kind") == "repo":
        if key == "flag":
            return G["hid"] if row.get("hidden") else ""
        if key == "repo":
            return "  " + row["repo"]
        return row["now"] if key == "task" else ""
    if key == "flag":
        f = ""
        if row["status"] == "ring":
            f += G["ring"]
        if row["dejavu"]:
            f += G["loop"]
        if row["status"] == "sentinel":
            f += G["dead"]
        if row.get("hidden"):
            f = G["hid"] + f
        return f[:2]
    if key == "repo":
        return row["repo"]
    if key == "task":
        if row["task"]:
            return row["task"]
        # the title survives death: you need it to know what a sentinel was, to resume it
        return f"\"{row['title']}\"" if row.get("title") else ("(no anderson task)" if row["status"] != "sentinel" else "")
    if key == "persona":
        return f"{row['pglyph']} {row['persona']}"
    if key == "stage":
        s = row["stage"] or "—"
        if row.get("iteration") is not None and row.get("max_iter"):
            s += f" {row['iteration']}/{row['max_iter']}"
        return s
    if key == "tier":
        return TIER_LABEL.get(row.get("tier") or "", "")
    if key == "model":
        return row["model"]
    if key == "now":
        return row["now"]
    if key == "cost":
        return f"{row['cost']:.2f}" if row["cost"] is not None else "—"
    if key == "ctx":
        return ctx_bar(row["ctx_pct"])
    if key == "ctxp":
        return f"{int(row['ctx_pct'])}%" if row["ctx_pct"] is not None else "—"
    if key == "age":
        return age_str(row["start"])
    return ""


def header_tail(frame):
    if THEME.get("rain"):
        return "  " + G["rain"][frame % 4]
    if THEME.get("spin"):
        return "  " + (SPIN[frame % 4] if not is_ascii() else "|/-\\"[frame % 4])
    if THEME.get("pulse"):
        return "  " + ("·" if frame % 2 else " ")
    return ""


def next_step(r):
    """What the human does next for this row, in one line."""
    if r.get("kind") == "section":
        return "space folds the repo list"
    if r.get("kind") == "repo":
        return f"{'enter' if is_ascii() else '⏎'} or N spawns an agent here · b hides the repo"
    st, gate, task = r.get("stage") or "", r.get("gate") or "", r.get("task") or ""
    if r["status"] == "sentinel":
        return f"{'enter' if is_ascii() else '⏎'} revives it in a new terminal · b dismisses the row"
    if st == "grill":
        return "answer the interrogation in the session (⏎), it hardens plan.md"
    if st == "plan_review" and gate == "human":
        return f"read plan.md (o) → /anderson:approve-plan {task}  · or say what to change"
    if st == "diff_review" and gate == "human":
        v = r.get("diff_verdict") or ""
        return f"read plan.md + audit.md + diff (o) → /anderson:approve-diff {task}" + (f"  · verdict {v}: /anderson:rework {task}" if v == "fix_first" else "")
    if st == "implement":
        return "NEO is writing code; nothing to do until diff review"
    if st == "repair":
        return "tests went red — TRINITY is root-causing them; nothing to do until diff review"
    if st == "done":
        return "shipped. PR is up; read what you merged"
    if r["status"] == "ring":
        return "the session waits for your next prompt (⏎)"
    return "working; come back when it rings"


def _wrap(txt, width, max_lines):
    """Word-wrap to `width` cells, at most `max_lines` lines, the last one ellipsized."""
    words, out, cur = str(txt).split(), [], ""
    for w in words:
        cand = (cur + " " + w) if cur else w
        if dw(cand) <= width:
            cur = cand
        else:
            out.append(cur); cur = w
            if len(out) == max_lines:
                break
    if cur and len(out) < max_lines:
        out.append(cur)
    if len(out) > max_lines or (len(out) == max_lines and dw(" ".join(words)) > sum(dw(x) for x in out) + len(out) - 1):
        out = out[:max_lines]; out[-1] = fit(out[-1] + " …", width).rstrip()
    return out or [""]


def detail_card(r, W, toast, t, airy=False):
    """Multi-line detail for the selected row. Labelled, one fact per line, no guessing needed.
    airy=True (16+ free lines): blank lines between groups, wider labels, `last` wraps to 2 lines."""
    d = G["det"]
    if r.get("kind"):
        lines = [("det", fit(d, W))]
        lw = 11 if airy else 9
        def L(label, txt):
            lines.append(("det", fit(f"{d} {label:<{lw}}{txt}", W)))
        L("name", r["repo"] + (f" · {r['path']}" if r.get("path") else ""))
        L("status", r["now"])
        L("next", next_step(r))
        lines.append(("quote", fit(f"{d} {toast}" if toast else f"{d} ", W)))
        return lines
    la, lr = r["lines"]
    head = r["task"] or (f"\"{r['title']}\"" if r.get("title") else r["repo"])
    who = f"{r['pglyph']} {r['persona']}" + (f" · {r['stage']}" if r.get("stage") else "") + (f" {r['iteration']}/{r['max_iter']}" if r.get("max_iter") else "")
    lines = []
    lw = 11 if airy else 9
    def L(label, txt, kind="det"):
        body_w = W - dw(d) - 1 - lw
        parts = _wrap(txt, body_w, 2 if (airy and label == "last") else 1)
        lines.append((kind, fit(f"{d} {label:<{lw}}{parts[0]}", W)))
        for extra in parts[1:]:
            lines.append((kind, fit(f"{d} {'':<{lw}}{extra}", W)))
    def gap():
        if airy:
            lines.append(("det", fit(d, W)))
    gap()
    L("task", f"{head} · {r['repo']}" + (f" · ⎇ {r['branch']}" if r.get("branch") else ""))
    L("who", who + (f" · model {r['model']}" if r.get("model") else "")
               + (f" · tier {TIER_LABEL.get(r.get('tier') or '', '')}" if r.get("tier") else ""))
    if r.get("stage"):
        L("verdicts", f"plan {r['plan_verdict'] or '—'} · diff {r['diff_verdict'] or '—'} · gate {r.get('gate') or 'none'}")
    gap()
    seen = age_str(r.get("last_seen")) if r.get("last_seen") else "—"
    L("status", f"{r['now']} · last activity {seen} ago · session age {age_str(r.get('start'))}")
    toks = f" ({r['ctx_tokens'] // 1000}k tokens)" if r.get("ctx_tokens") else ""
    ctx = f"{ctx_bar(r['ctx_pct'])}{toks}" if r.get("ctx_pct") is not None else "unknown (no heartbeat yet)"
    hot = "  ← /compact" if (r.get("ctx_pct") or 0) >= HOT_CTX and r["status"] != "sentinel" else ""
    pm = f" · lines +{la} −{lr}" if la is not None else ""
    cost = f" · api est ${r['cost']:.2f}" if (SHOW_COST and r.get("cost") is not None) else ""
    L("context", f"{ctx}{hot}{pm}{cost}")
    total, running, last_agent = r.get("agents") or (0, 0, "")
    if total:
        run = f" · {running} running" if running else ""
        L("agents", f"{total} sent{run}" + (f" · last {last_agent}" if last_agent else ""))
    where = r["tmux_addr"] or r["tmux_pane"] or r.get("start_cwd") or r["cwd"] or "?"
    L("where", f"{where} · pid {r['pid'] or '?'} · session {r['sid'][:8]}")
    gap()
    if r.get("title") and r["task"]:
        L("prompt", f"\"{r['title']}\"")
    L("last", r["text"] or r["now"])
    L("next", next_step(r))
    gap()
    q = quote_for(r, t)
    lines.append(("quote", fit(f"{d} {toast}" if toast else (f"{d} \"{q}\"" if q else f"{d} "), W)))
    return lines


def _row_window(rows, W, filt, height, sel):
    """(offset, count) of the row slice that keeps the footer, the card and the cursor on
    screen when there are more rows than the terminal has lines. height=None (the --once path)
    or everything already fits -> (0, len(rows)): no window, nothing changes.
    ponytail: header (3) + >=1 row + rule + compact card (3) + footer (>=2) is a ~13-line floor
    that no windowing can shrink further; terminals under it lose the footer to run_tui's outer
    `lines[: h - 1]` slice. Pre-existing floor of fleet's whole render layout, not new here."""
    if not height or not rows:
        return 0, len(rows)
    foot_n = len(footer(rows, W, filt))
    head_n = 3 + (1 if usage_limits(bars=True) else 0)   # hdr, rule, colhdr [+ usage line]
    tail_n = 1 + 3 + foot_n                              # rule + compact 3-line card + footer
    visible = max(1, height - head_n - tail_n)
    if visible >= len(rows):
        return 0, len(rows)
    off = max(0, min(sel - visible // 2, len(rows) - visible))
    return off, visible


def render(rows, width, sel=0, frame=0, filt="", toast="", burst=(), t=None, height=None, ws=None, all_rows=None):
    """Pure: -> list of (kind, line). Every line is exactly `width` cells (see --selftest).
    all_rows (the full session list, before the filter) drives the header/footer aggregates;
    defaults to `rows`."""
    t = time.time() if t is None else t
    W = max(40, width)
    cols = layout(W)
    lines = []
    sess_rows = [r for r in (all_rows if all_rows is not None else rows) if not r.get("kind")]
    n_ring = sum(r["status"] == "ring" for r in sess_rows)
    n_hid = sum(bool(r.get("hidden")) for r in sess_rows)
    n_dead = sum(r["status"] == "sentinel" and not r.get("hidden") for r in sess_rows)
    n_live = len(sess_rows) - n_dead - n_hid
    ws_name = os.path.basename((ws or "").rstrip("/"))
    left = f"{G['eyes']}  T H E  O P E R A T O R" + (f" · {ws_name}" if ws_name else "")
    right = f"{words('fleet')} · {n_live} {words('live')} · {n_ring} {words('ring')} · {n_dead} {words('deads' if n_dead != 1 else 'dead')}{f' · {n_hid} hidden' if n_hid else ''}{header_tail(frame)}"
    lines.append(("hdr", fit(fit(left, max(0, W - dw(right) - 1)) + " " + right, W)))
    lim = usage_limits(bars=True)
    if lim:                                      # the plan's windows: the number to keep an eye on, so it lives up here
        lines.append(("usage_hot" if usage_hot() else "usage", fit(f"{G['det']} {THEME['name']} · {lim}", W)))
    foot = footer(rows, W, filt, all_rows=all_rows)
    off, vis_n = _row_window(rows, W, filt, height, sel)
    view = rows[off:off + vis_n]
    # tall terminal (16+ free lines after the list and the footer): blank lines around the rules, so it breathes
    airy = bool(height) and height - (len(lines) + len(view) + 4 + len(foot)) >= 16
    def sp():
        if airy:
            lines.append(("empty", fit("", W)))
    sp()
    lines.append(("rule", rule(W)))
    sp()
    hdr = " " * PREFIX + "  ".join(fit(tt, w, a) for _, tt, w, a in cols)
    lines.append(("colhdr", fit(hdr, W)))
    if not rows:
        lines.append(("empty", fit("", W)))
        lines.append(("empty", fit("   " + words("empty"), W)))
    for i, r in enumerate(view):
        idx = i + off
        cur = G["cur"] if idx == sel else " "
        num = str(idx + 1) if idx < 9 else " "
        if r["sid"] in burst:
            body = "".join(random.choice("01·10 1 0") for _ in range(W - PREFIX))
            kind = "burst"
        elif r.get("kind"):                    # repo / section: the name spans the repo + task columns
            nw = max(sum(w for k, _, w, _ in cols if k in ("repo", "task")) + 2, min(48, W - PREFIX - 30))
            body = fit(cell(r, "flag", frame), 2) + "  " + fit(cell(r, "repo", frame), nw) + "  " + fit(r["now"], max(0, W - PREFIX - nw - 6))
            kind = ("hidden" if r.get("hidden") else r["kind"]) + ("_sel" if idx == sel else "")
        else:
            body = "  ".join(fit(cell(r, k, frame), w, a) for k, _, w, a in cols)
            kind = ("hidden" if r.get("hidden") else "shipped" if r.get("shipped") else "idle" if r.get("idle") else r["status"]) + ("_sel" if idx == sel else "")
        lines.append((kind, fit(f"{num}{cur} {body}", W)))
    sp()
    lines.append(("rule", rule(W)))
    sp()                                        # one more before the card: the rule, air, then the task
    d = G["det"]
    # detail: a labelled card when the terminal has room (>= 10 free lines), else the 3-line compact form
    room = (height - len(lines) - len(foot)) if height else 3
    if rows and 0 <= sel < len(rows):
        r = rows[sel]
        if room >= 10:
            lines += detail_card(r, W, toast, t, airy=airy or room >= 16)
        elif r.get("kind"):
            l1 = f"{d} {r['repo']}{(' · ' + r['path']) if r.get('path') else ''} · {r['now']}"
            l2 = f"{d} {next_step(r)}"
            q = quote_for(r, t)
            l3 = f"{d} {toast}" if toast else (f"{d} \"{q}\"" if q else f"{d} ")
            lines += [("det", fit(l1, W)), ("det", fit(l2, W)), ("quote", fit(l3, W))]
        else:
            la, lr = r["lines"]
            pm = f"+{la} −{lr}" if la is not None else ""
            it = f"iteration {r['iteration']}/{r['max_iter']} · " if r.get("max_iter") else ""
            where = r["tmux_addr"] or r["tmux_pane"] or (f"pid {r['pid']}" if r["pid"] else "no pane")
            br = f" · ⎇ {r['branch']}" if r.get("branch") else ""
            head_txt = r['task'] or (f"\"{r['title']}\"" if r.get("title") else r['repo'])
            l1 = f"{d} {head_txt}{br} · {r['persona']} · {it}plan: {r['plan_verdict'] or '—'} · diff: {r['diff_verdict'] or '—'} · {pm} · {where}"
            l2 = f"{d} last: {r['text'] or r['now']}"
            q = quote_for(r, t)
            l3 = f"{d} {toast}" if toast else (f"{d} \"{q}\"" if q else f"{d} ")
            lines += [("det", fit(l1, W)), ("det", fit(l2, W)), ("quote", fit(l3, W))]
    else:
        l1 = f"{d} " + ("filter: " + filt if filt else "")
        l2 = f"{d} {toast}" if toast else f"{d} "
        lines += [("det", fit(l1, W)), ("det", fit(l2, W)), ("quote", fit(f"{d} ", W))]
    if height:                                   # pin the footer to the bottom; the card keeps the middle
        while len(lines) + len(foot) < height:
            lines.append(("det", fit(d, W)))
    return lines + foot


def footer(rows, W, filt="", all_rows=None):
    """Bottom of the screen: rule, the keys (wrapped, never truncated), then usage on its own line."""
    d = G["det"]
    fleet = sum(r["cost"] or 0 for r in (all_rows if all_rows is not None else rows))
    lim = usage_limits()
    keys = ("↑↓ tune · ⏎/1-9 jack in · N new agent · w next ring · o read plan · r kill · b hide · h hidden · "
            "space fold · m sound · / filter · ? manual · q quit")
    if is_ascii():
        keys = keys.replace("↑↓", "jk").replace("⏎", "enter")
    if filt:
        keys = f"/{filt}_   (esc clears)"
    usage = ""
    if not lim:
        usage = f"{THEME['name']} · api est ${fleet:.2f}"
    elif SHOW_COST:
        usage = f"api est ${fleet:.2f} (the plan is a flat fee; this is what the tokens would cost on the API)"
    out = [("rule", rule(W))]
    kw, klines, cur = W - dw(d) - 1, [], ""
    for grp in keys.split(" · "):               # wrap between key groups, never inside one
        cand = f"{cur} · {grp}" if cur else grp
        if dw(cand) <= kw or not cur:
            cur = cand
        else:
            klines.append(cur); cur = grp
    klines.append(cur)
    out += [("foot", fit(f"{d} {k}", W)) for k in klines[:3]]
    if usage:
        out.append(("foot", fit(f"{d} {usage}", W)))
    return out


def _reset_str(ts):
    """'4h07 left' / '38m left' inside a day, else 'resets Fri 19:00'."""
    if not ts:
        return ""
    left = int(ts - time.time())
    if left <= 0:
        return ""
    if left < 3600:
        return f"{left // 60}m left"
    if left < 86400:
        return f"{left // 3600}h{(left % 3600) // 60:02d} left"
    return time.strftime("resets %a %H:%M", time.localtime(ts))


USAGE_HOT = 90   # % of a subscription window past which the footer paints red: credits are next


def usage_hot():
    """True when any /usage window is past USAGE_HOT."""
    best, best_ts = None, 0
    for p in glob.glob(os.path.join(FLEET_DIR, "*.status.json")):
        d = jload(p) or {}
        if d.get("limits") and (d.get("ts") or 0) > best_ts:
            best, best_ts = d["limits"], d["ts"]
    return bool(best) and any((w or {}).get("pct") is not None and w["pct"] >= USAGE_HOT for w in best.values())


def usage_limits(bars=False):
    """Subscription windows from the freshest heartbeat that carries them (account-wide, so any
    session's copy is the truth), in words:
      'session 46% · 4h07 left │ week 41% · resets Fri 19:00'
    bars=True adds a 10-cell bar before each percentage (the header line).
    session = the rolling 5-hour window /usage calls "Current session"; week = the 7-day window
    for all models. Claude Code does not expose the per-model weekly number. Empty when no
    heartbeat has limits (API-key users)."""
    best, best_ts = None, 0
    for p in glob.glob(os.path.join(FLEET_DIR, "*.status.json")):
        d = jload(p) or {}
        if d.get("limits") and (d.get("ts") or 0) > best_ts:
            best, best_ts = d["limits"], d["ts"]
    if not best:
        return ""
    age = time.time() - best_ts
    if age > 6 * 3600:
        return ""                                     # nobody has talked to the API in hours: no number beats a wrong one
    parts = []
    for key, label in (("five_hour", "session"), ("seven_day", "week"), ("spend_limit", "spend")):
        w = best.get(key) or {}
        if w.get("pct") is None:
            continue
        r = _reset_str(w.get("resets_at"))
        n = max(0, min(10, int(round(float(w["pct"]) / 10))))
        bar = (G["bar"] * n + G["trk"] * (10 - n) + " ") if bars else ""
        parts.append(f"{label} {bar}{int(w['pct'])}%" + (f" · {r}" if r else ""))
    sep = " │ " if not is_ascii() else " | "
    stale = f" (as of {age_str(best_ts)} ago)" if age > 120 else ""   # numbers come from the last API reply any session saw
    return sep.join(parts) + stale


MANUAL = """
  ⌐■-■  T H E  O P E R A T O R                                          dodge this

  Top: every Claude Code session on this machine, ringing first. Below: the repos of the
  workspace fleet was launched from, where N starts a new agent.

  ☎  ring 12m    the session waits on you (turn ended, permission prompt, a question), and for
                 how long. It rings once, 5 s after it starts waiting, so a turn that carries on
                 by itself never rings. After 5 minutes the row goes white and still
  ▶  work        model thinking, or a tool / subagent running
  ✝  sentinel    the process is gone; the row stays until you hide it with b
  ⟲  déjà vu     the loop repeated (iteration > 0)
  red ctx        context past 80%: /compact before the next review eats the budget

  persona   who is on the job, from feature-research/*/state.md: ARCHITECT plan,
            INTERROGATOR grill (you), ORACLE plan_review, NEO implement, TRINITY repair,
            AGENT SMITH diff_review, THE ONE shipped, T. ANDERSON: no pipeline yet
  tier      triv · normal · HARD · CRITICAL, from state.md `tier`
  header    session / week bars are your /usage windows (red past 90%)

  ↑↓ / j k  tune         select a row
  ⏎ / 1-9   jack in      bring that session's terminal tab to the front (Ghostty, iTerm2,
                         Terminal.app, or the tmux pane). On a sentinel: reopen it with
                         claude --resume in a new tab. On a repo: same as N
  N         new agent    prompt box, then p plain claude · a /anderson:start · A /anderson:auto,
                         in a new tab of its own. A repo parked on a feature branch gets a
                         worktree (.worktrees/<task>, branch anderson/<task>) so the work in
                         progress there is never touched. On a session row: its repo
  w         next ring    jump to the session that has waited longest
  o         read         plan.md / audit.md right here (glow, else less), then the code diff at
                         diff review. q comes back
  r         kill         SIGTERM the session (asks first); the row goes with it
  b         hide         hide a row or a repo (the process is left alone); on a hidden one: show it
  h         hidden       list the hidden rows and repos too, dim
  space     fold         fold / unfold the repo list (saved)
  m         sound        ring sound on/off, for every running fleet at once (saved)
  /         filter       substring on repo · task ; esc clears
  ?         this         any key closes
  q         quit

  back to fleet from a session: `fleet --focus` brings this tab forward (bind it to a hotkey).
  flags: --theme NAME · --plain · --calm · --cost · --notify · --ring NAME · --rings · --play all
         --ping · --demo · --once · --ascii · --no-intro.  prefs: ~/.claude/fleet/prefs.json
"""


# ─────────────────────────────────────────────────────────────────── curses
def _colors(curses):
    """name -> curses attr for the active theme; 256-colour where available, 8-colour fallback."""
    if not curses.has_colors():
        return lambda name: curses.A_DIM if name == "dim" else 0
    curses.start_color(); curses.use_default_colors()
    many = curses.COLORS >= 256
    table = {  # name: (256-colour index, 8-colour fallback)
        "green": (40, curses.COLOR_GREEN), "white": (252, curses.COLOR_WHITE), "amber": (214, curses.COLOR_YELLOW),
        "yellow": (226, curses.COLOR_YELLOW), "cyan": (51, curses.COLOR_CYAN), "blue": (75, curses.COLOR_BLUE),
        "red": (196, curses.COLOR_RED), "dim": (243, curses.COLOR_WHITE),
    }
    pairs = {}
    for i, (name, (c256, c8)) in enumerate(table.items(), start=1):
        curses.init_pair(i, c256 if many else c8, -1)
        pairs[name] = curses.color_pair(i) | (curses.A_DIM if name == "dim" and not many else 0)
    return lambda name: pairs.get(name, 0)


# ─────────────────────────────────────────────────────── notify · resume
NOTIFY = False


def _terminal_bundle():
    return {"Apple_Terminal": "com.apple.Terminal", "iTerm.app": "com.googlecode.iterm2",
            "WarpTerminal": "dev.warp.Warp-Stable", "ghostty": "com.mitchellh.ghostty"}.get(os.environ.get("TERM_PROGRAM", ""))


def notify(title, body, sid=None):
    """Desktop banner when a session starts waiting or crosses the context line. Fire-and-forget,
    and silent: the ring sound is `m`'s job alone, so muting fleet mutes everything.
    macOS: terminal-notifier when installed (reliable; clicking the banner runs `--jack <sid>`,
    which brings that session's tab forward); else osascript, which recent macOS often swallows.
    Linux: notify-send."""
    try:
        if sys.platform == "darwin":
            if shutil.which("terminal-notifier"):
                cmd = ["terminal-notifier", "-title", "THE OPERATOR", "-subtitle", title, "-message", body,
                       "-group", "anderson-fleet"]
                if sid:
                    cmd += ["-execute", f"{shlex_quote(sys.executable)} {shlex_quote(os.path.abspath(__file__))} --jack {shlex_quote(sid)}"]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            esc = lambda t: t.replace("\\", "\\\\").replace('"', '\\"')
            subprocess.Popen(["osascript", "-e", f'display notification "{esc(body)}" with title "THE OPERATOR" subtitle "{esc(title)}"'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which("notify-send"):
            subprocess.Popen(["notify-send", f"THE OPERATOR · {title}", body], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


SOUND = False
RING = "phone"                                                        # which bundled/own sound rings
RING_WAV = os.path.join(FLEET_DIR, "ring.wav")                       # yours, if you drop one here: always wins
SOUNDS_BUNDLED = os.path.join(HERE, "..", "assets", "sounds")        # phone, snare, hitech, freeze, blip, rift, jump
SOUNDS_USER = os.path.join(FLEET_DIR, "sounds")                      # drop more .wav here; picked by name like the bundled ones


def sound_names():
    """Ring sounds you can pick from: bundled first (phone leads), then your ~/.claude/fleet/sounds/*.wav."""
    names = []
    for d in (SOUNDS_BUNDLED, SOUNDS_USER):
        for f in sorted(glob.glob(os.path.join(d, "*.wav"))):
            n = os.path.basename(f)[:-4]
            if n not in names:
                names.append(n)
    if "phone" in names:
        names.remove("phone"); names.insert(0, "phone")
    return names


def sound_file(name):
    for d in (SOUNDS_USER, SOUNDS_BUNDLED):
        f = os.path.join(d, name + ".wav")
        if os.path.isfile(f):
            return f
    return None


def ring_path():
    """Which sound rings: your ~/.claude/fleet/ring.wav, else the picked sound (RING; --ring NAME), else the bundled phone, else a synthesized ringback written once to the fleet dir."""
    if os.path.isfile(RING_WAV):
        return RING_WAV
    f = sound_file(RING) or sound_file("phone")
    if f:
        return f
    synth = os.path.join(FLEET_DIR, "ring-synth.wav")
    if not os.path.isfile(synth):
        make_ring_wav(synth)
    return synth


def make_ring_wav(path):
    """Synthesize the phone: classic ringback (440 + 480 Hz), two 0.35s bursts. Drop your own
    ring.wav at the same path to replace it. Stdlib only."""
    import math, struct, wave
    rate, amp = 22050, 0.35
    frames = bytearray()
    def tone(sec, on):
        n = int(rate * sec)
        for i in range(n):
            t = i / rate
            v = amp * (math.sin(2 * math.pi * 440 * t) + math.sin(2 * math.pi * 480 * t)) / 2 if on else 0.0
            env = min(1.0, i / (rate * 0.01), (n - i) / (rate * 0.03)) if on else 0.0     # click-free edges
            frames.extend(struct.pack("<h", int(v * env * 32767)))
    tone(0.35, True); tone(0.18, False); tone(0.35, True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(bytes(frames))


def ring_sound():
    """Play the ring, fire-and-forget. macOS afplay; Linux paplay / aplay."""
    try:
        path = ring_path()
        for player in (["afplay"], ["paplay"], ["aplay", "-q"]):
            if shutil.which(player[0]):
                subprocess.Popen(player + [path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
    except Exception:
        pass
    return False


def resume_cmd(r):
    # repo/section rows have no session to resume
    if r.get("kind"):
        return None
    sid = r.get("sid") or ""
    if sid.startswith("pid:") or sid.startswith("demo") or len(sid) < 8:
        return None
    return f"claude --resume {sid}"


def shlex_quote(s):
    import shlex
    return shlex.quote(s)


def copy_cmd(cmd):
    """Put `cmd` on the clipboard (pbcopy / wl-copy / xclip), or say it plainly when none exist."""
    for tool in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
        if shutil.which(tool[0]):
            try:
                subprocess.run(tool, input=cmd, text=True, timeout=3)
                return f"copied: {cmd}"
            except Exception:
                break
    return f"run: {cmd}"


NEW_TAB_ITERM = """tell application "iTerm2"
	activate
	if (count of windows) > 0 then
		tell current window to create tab with default profile
	else
		create window with default profile
	end if
	tell current session of current window to write text "{cmd}"
end tell"""

# Ghostty 1.3+ ships an AppleScript dictionary; initial input runs cmd in your login shell, like iTerm's write text
NEW_TAB_GHOSTTY = """tell application "Ghostty"
	activate
	set cfg to new surface configuration
	set initial input of cfg to "{cmd}" & return
{wd}	if (count of windows) > 0 then
		new tab in front window with configuration cfg
	else
		new window with configuration cfg
	end if
end tell"""

NEW_WINDOW_TERMINAL = """tell application "Terminal"
	activate
	do script "{cmd}"
end tell"""


def _host_terminal():
    """The macOS terminal app fleet runs in: "Ghostty", "iTerm2", else "Terminal". __CFBundleIdentifier
    first: macOS sets it for a GUI app's children and it survives tmux (where TERM_PROGRAM says "tmux")."""
    # ponytail: under tmux this is whichever terminal started the tmux server, not the attached client
    b = os.environ.get("__CFBundleIdentifier") or _terminal_bundle()
    return {"com.mitchellh.ghostty": "Ghostty", "com.googlecode.iterm2": "iTerm2"}.get(b, "Terminal")


def new_terminal(cmd, cwd=None, name=None, verb="spawned"):
    """A new terminal already running `cmd` in `cwd`, never the one fleet is in. macOS: a new tab in
    the terminal app fleet runs in (Ghostty / iTerm2; a Terminal.app window), started in `cwd` so
    the tab's directory names the repo. Elsewhere: a detached tmux window when fleet is in tmux.
    Else the command lands on the clipboard."""
    full = f"cd {shlex_quote(cwd)} && {cmd}" if cwd else cmd
    if sys.platform == "darwin":
        app = _host_terminal()
        tmpl = {"Ghostty": NEW_TAB_GHOSTTY, "iTerm2": NEW_TAB_ITERM}.get(app, NEW_WINDOW_TERMINAL)
        # the shell sees cmd verbatim; only the AppleScript string literal needs escaping
        esc = lambda t: t.replace("\\", "\\\\").replace('"', '\\"')
        wd = f'\tset initial working directory of cfg to "{esc(cwd)}"\n' if cwd else ""
        script = tmpl.replace("{wd}", wd).replace("{cmd}", esc(full))
        try:
            rc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=15)
            if rc.returncode == 0:
                return f"Operator. {verb} in a new {app} {'window' if app == 'Terminal' else 'tab'}."
            return f"launch failed: {rc.stderr.strip() or 'osascript'}  ·  {copy_cmd(full)}"
        except Exception as e:
            return f"launch failed: {e}  ·  {copy_cmd(full)}"
    if os.environ.get("TMUX"):
        try:
            args = ["tmux", "new-window", "-d"] + (["-c", cwd] if cwd else []) + (["-n", name] if name else []) + [cmd]
            subprocess.run(args, timeout=5, check=True)
            return f'Operator. {verb} in tmux window "{name or cmd.split()[0]}" (prefix+n to reach it).'
        except Exception as e:
            return f"launch failed: {e}  ·  {copy_cmd(full)}"
    # ponytail: no portable "open a new terminal window" off macOS/tmux. Add one if someone asks on Linux.
    return copy_cmd(full)


def revive(r):
    """A sentinel has no terminal left to jack into, so give it one: a new tab already running
    `claude --resume <sid>` where the session lived."""
    cmd = resume_cmd(r)
    if not cmd:
        return "no session id for that row."
    return new_terminal(cmd, cwd=r.get("start_cwd") or r.get("cwd") or None, verb="resumed")


# ──────────────────────────────────────────────────────────────────── spawn: N on a repo
def slug(prompt):
    """The window name / phase-3 task-dir key: an issue id (LIN-482) lowercased, else the first
    words slugified to <=32 chars, else task-<HHMM>. [^a-z0-9-] stripped: no `:` and no `.`,
    both of which break a tmux target."""
    prompt = (prompt or "").strip()
    m = re.match(r"^([A-Za-z]{2,10}-\d+)", prompt)
    if m:
        s = m.group(1).lower()
    elif prompt:
        s = re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", prompt.lower())).strip("-")[:32].strip("-")
    else:
        s = ""
    return s or ("task-" + time.strftime("%H%M"))


def _git(args, cwd):
    """git in `cwd`: stdout stripped on success (possibly ""), None when git fails or is missing."""
    try:
        r = subprocess.run(["git", "-C", cwd] + args, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def default_branch(path):
    """origin's HEAD when the remote says, else whichever of main/master exists, else None."""
    head = _git(["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], path)
    if head:
        return head.split("/", 1)[1] if "/" in head else head
    for b in ("main", "master"):
        if _git(["rev-parse", "--verify", "--quiet", b], path):
            return b
    return None


def worktree_for(path, task):
    """(cwd, note) for a spawn into `path`. A repo parked on a feature branch is someone's work in
    progress, so the agent never lands in it: it gets `<repo>/.worktrees/<task>` on branch
    `anderson/<task>`, cut from the default branch. On the default branch the checkout is free and
    we use it as-is. Anything git can't do (no repo, no default branch, `worktree add` refuses)
    falls back to the repo itself with a note saying so — a spawn is never blocked by this."""
    cur = _git(["rev-parse", "--abbrev-ref", "HEAD"], path)
    if not cur:
        return path, ""
    base = default_branch(path)
    if not base or cur == base:
        return path, ""
    wt = os.path.join(path, ".worktrees", task)
    if os.path.isdir(wt):
        return wt, f"worktree .worktrees/{task} (reused) — {os.path.basename(path)} stays on {cur}"
    start = f"origin/{base}" if _git(["rev-parse", "--verify", "--quiet", f"origin/{base}"], path) else base
    if _git(["worktree", "add", "-b", f"anderson/{task}", wt, start], path) is None:
        _git(["worktree", "add", wt, f"anderson/{task}"], path)      # branch already exists
    if not os.path.isdir(wt):
        return path, f"worktree failed — running in {os.path.basename(path)}, still on {cur}"
    return wt, f"worktree .worktrees/{task} on anderson/{task} (off {start}) — {os.path.basename(path)} stays on {cur}"


def spawn_cmd(row, prompt, mode):
    """(cwd, shell_cmd, window_name) for `N` on a repo row. Pure. mode: p = bare `claude <prompt>`,
    a/A = /anderson:start|auto <slug> <prompt> (both commands take the FIRST WORD as the task key,
    so the slug has to lead)."""
    cwd = row["path"]
    prompt = (prompt or "").strip()
    if not prompt:
        return cwd, "claude", row["repo"]
    s = slug(prompt)
    if mode == "a":
        cmd = f"claude {shlex_quote('/anderson:start ' + s + ' ' + prompt)}"
    elif mode == "A":
        cmd = f"claude {shlex_quote('/anderson:auto ' + s + ' ' + prompt)}"
    else:
        cmd = f"claude {shlex_quote(prompt)}"
    return cwd, cmd, f"{row['repo']}:{s}"


def launch_agent(row, prompt, mode):
    """`N` → prompt box → p/a/A: spawn a claude agent into a repo, in a terminal of its own.
    Stateless: spawn fires new_terminal() and forgets; the session shows up through its hooks."""
    if not shutil.which("claude"):
        return "claude not on PATH: install it first."
    cwd, cmd, window = spawn_cmd(row, prompt, mode)
    note = ""
    if (prompt or "").strip():
        cwd, note = worktree_for(cwd, slug(prompt))
    msg = new_terminal(cmd, cwd=cwd, name=window)
    return f"{msg}  ·  {note}" if note else msg


# ──────────────────────────────────────────────────────── open the gate artifact
def gate_files(r):
    """The artifacts a human gate asks you to read, for this row's stage. Existing files only."""
    root, task = r.get("root") or r.get("cwd") or "", r.get("task") or ""
    if not root or not task:
        return []
    d = os.path.join(root, "feature-research", task)
    want = {"grill": ["plan.md"], "plan_review": ["plan.md"], "diff_review": ["plan.md", "audit.md"],
            "implement": ["audit.md"]}.get(r.get("stage") or "", ["plan.md"])
    return [os.path.join(d, f) for f in want if os.path.isfile(os.path.join(d, f))]


def md_ansi(text):
    """Markdown to ANSI for `less -R`: headings bold green, bullets green, bold, ~~strike~~ dim
    struck (the plan-reviewer's edits), fenced code dim. Stdlib only, good enough to read a plan."""
    B, D, G_, S, R = "\033[1m", "\033[2m", "\033[32m", "\033[9m", "\033[0m"
    out, code = [], False
    for ln in text.split("\n"):
        if ln.startswith("```"):
            code = not code; out.append(D + ln + R); continue
        if code:
            out.append(D + ln + R); continue
        ln = re.sub(r"\*\*(.+?)\*\*", B + r"\1" + R, ln)
        ln = re.sub(r"~~(.+?)~~", D + S + r"\1" + R, ln)
        ln = re.sub(r"`([^`]+)`", D + r"\1" + R, ln)
        if ln.startswith("#"):
            out.append(B + G_ + ln.lstrip("# ") + R)
        elif re.match(r"^\s*([-*]|\d+\.)\s", ln):
            out.append(re.sub(r"^(\s*)([-*]|\d+\.)", r"\1" + G_ + r"\2" + R, ln, 1))
        elif ln.startswith("|"):
            out.append(D + ln + R if set(ln) <= set("|-: ") else ln)
        else:
            out.append(ln)
    return "\n".join(out)


def view_cmd(files):
    """How `o` reads a file inside the fleet terminal: glow (rendered markdown) when installed, else
    less -R over a stdlib ANSI rendering. Returns (argv, temp files to delete afterwards)."""
    if shutil.which("glow"):
        width = max(40, shutil.get_terminal_size((100, 40)).columns - 2)   # glow wraps at 80 unless told the width
        return ["glow", "-p", "-w", str(width)] + files, []
    tmp = []
    for f in files:
        t = os.path.join(FLEET_DIR, "view-" + os.path.basename(f))
        try:
            os.makedirs(FLEET_DIR, exist_ok=True)
            with open(t, "w") as out:
                out.write(md_ansi(open(f, errors="replace").read()))
            tmp.append(t)
        except Exception:
            tmp.append(f)
    names = " · ".join(os.path.basename(f) for f in files)
    return ["less", "-R", "-P", f"{names}  (q back to fleet, :n next file)"] + tmp, [t for t in tmp if t.startswith(FLEET_DIR)]


def gate_diff(r):
    """Gate 2's code diff, uncommitted until approve-diff ships it: tracked changes vs HEAD plus
    untracked files, coloured, into a temp file for less. Read-only (no `git add -N`), scratch dir
    left out. None when not diff review, not a git repo, or nothing changed."""
    root = r.get("root") or r.get("cwd") or ""
    if r.get("stage") != "diff_review" or not root:
        return None
    git, skip = ["git", "-C", root], ["--", ".", ":(exclude)feature-research"]
    try:
        out = subprocess.run(git + ["diff", "--color=always", "HEAD"] + skip, capture_output=True, text=True).stdout
        new = subprocess.run(git + ["ls-files", "--others", "--exclude-standard", "-z"] + skip,
                             capture_output=True, text=True).stdout
        for f in filter(None, new.split("\0")):   # --no-index exits 1 on a difference: never check=True
            out += subprocess.run(git + ["diff", "--no-index", "--color=always", "/dev/null", f],
                                  capture_output=True, text=True, cwd=root).stdout
        if not out.strip():
            return None
        os.makedirs(FLEET_DIR, exist_ok=True)
        path = os.path.join(FLEET_DIR, "view-code.diff")
        with open(path, "w") as fh:
            fh.write(out)
        return path
    except Exception:
        return None


def view_gate(r, scr=None):
    """`o`: read plan.md / audit.md right here, in the fleet terminal, then the code diff at diff
    review; the TUI resumes on q."""
    import curses
    files = gate_files(r)
    if not files:
        return "nothing to read: no plan.md / audit.md for that row."
    cmd, tmp = view_cmd(files)
    diff = gate_diff(r)
    if diff:
        tmp.append(diff)
    try:
        if scr is not None:
            curses.endwin()
        subprocess.run(cmd)
        if diff:   # its own pager: glow would flatten the colours
            subprocess.run(["less", "-R", "-P", "code diff  (q back to fleet)", diff])
    except Exception as e:
        return f"viewer failed: {e}"
    finally:
        for t in tmp:
            try:
                os.remove(t)
            except Exception:
                pass
        if scr is not None:
            scr.refresh()
    hint = "" if shutil.which("glow") else "   (brew install glow for rendered markdown)"
    return f"read {', '.join(os.path.basename(f) for f in files)}{' + code diff' if diff else ''}{hint}"


def _own_tty():
    try:
        return os.ttyname(sys.stdout.fileno())
    except Exception:
        return None


FLEET_TITLE = "⌐■-■ fleet"      # this tab's title while fleet runs: findable in the tab bar, and what --focus looks for
RING_SETTLE_S = 5               # a ring alerts only once it has lasted this long: a turn that carries on by itself never rings


def due_rings(rows, rung, now):
    """(rows to alert for now, new `rung`). A ring alerts once, and only after RING_SETTLE_S: a Stop
    another hook blocks (the scheduler chaining a stage) is followed by tool events within seconds,
    and must not ring. `rung` remembers what already alerted until it stops ringing."""
    ringing = {r["sid"]: r for r in rows if r["status"] == "ring" and not r.get("hidden")}
    settled = {sid for sid, r in ringing.items() if now - (r.get("since") or 0) >= RING_SETTLE_S}
    return [ringing[sid] for sid in sorted(settled - rung)], (rung & set(ringing)) | settled


def run_tui(args):
    import curses
    demo = "--demo" in args
    intro = "--no-intro" not in args
    tty = _own_tty()
    try:
        sys.stdout.write(f"\033]2;{FLEET_TITLE}\007"); sys.stdout.flush()
        os.makedirs(FLEET_DIR, exist_ok=True)
        with open(os.path.join(FLEET_DIR, "fleet.tty"), "w") as f:
            f.write(f"{tty or '-'} {os.getpid()}")
    except Exception:
        pass

    def app(scr):
        global NOTIFY, SOUND, RING, SHOW_HIDDEN
        curses.curs_set(0)
        scr.timeout(100)
        col = _colors(curses)
        BOLD, DIM, REV = curses.A_BOLD, curses.A_DIM, curses.A_REVERSE

        def attrs():
            T = THEME
            return {
                "hdr": col(T["hdr"]) | BOLD, "rule": col(T["accent"]) | DIM, "colhdr": DIM, "empty": col(T["hdr"]),
                "usage": col(T["hdr"]) | BOLD, "usage_hot": col("red") | BOLD,
                "work": 0, "work_sel": REV,
                "ring": col(T["ring"]) | BOLD, "ring_sel": col(T["ring"]) | BOLD | REV,
                "idle": col("white"), "idle_sel": col("white") | REV,
                "sentinel": col(T["dead"]) | DIM, "sentinel_sel": DIM | REV,
                "hidden": DIM, "hidden_sel": DIM | REV,
                "section": col(T["hdr"]) | BOLD, "section_sel": col(T["hdr"]) | BOLD | REV,
                "repo": DIM, "repo_sel": REV,
                "shipped": col("red") | BOLD, "shipped_sel": col("red") | BOLD | REV,   # final state: done, stands out
                "burst": col(T["accent"]) | BOLD, "det": 0, "quote": col(T["quote"]) | DIM, "foot": DIM,
            }

        if intro:
            boot(scr, curses, col)
        rows, all_rows, sel, filt, filt_mode = [], [], 0, "", False
        toast, toast_until = "", 0
        confirm, confirm_do = None, None
        manual = False
        rung, shipped, burst, hot_seen = set(), set(), {}, set()
        last_scan = 0
        last_full = 0          # a full repaint every FULL_REPAINT_S: a Space swipe or an app switch can leave stale cells
        prev = None            # last painted (size, lines-with-attrs): repaint only on change
        ws = workspace_root(os.getcwd())
        wp = ws_prefs(ws)
        hidden_repos, folded = set(wp["hidden"]), wp["folded"]
        prompt_mode, menu_mode, prompt_row, prompt_buf = False, False, None, ""
        pending_sel_sid = None

        def say(msg, secs=3):
            nonlocal toast, toast_until
            toast, toast_until = msg, time.time() + secs

        def spawn_into(row):
            """Open the spawn prompt box for a repo row, or for the repo a session row belongs to."""
            nonlocal prompt_mode, prompt_row, prompt_buf
            if row.get("kind") == "section":
                return "pick a repo to spawn into."
            prompt_mode, prompt_row, prompt_buf = True, (row if row.get("kind") == "repo" else repo_target(session_root(row))), ""
            return ""

        def toggle_fold():
            nonlocal folded, last_scan
            folded = not folded
            save_ws_prefs(ws, folded=folded); last_scan = 0

        def activate(row):
            """`⏎` / `1`-`9`: a session jacks in, a repo opens the spawn box, the section folds."""
            if row.get("kind") == "section":
                toggle_fold(); return ""
            if row.get("kind") == "repo":
                return spawn_into(row)
            return jack_in(row)

        def kill_row(r):
            """`r` confirmed: SIGTERM the session and hide its row."""
            nonlocal last_scan
            if not r["pid"]:
                return "no pid for that session (demo or unknown)"
            try:
                os.kill(int(r["pid"]), signal.SIGTERM)
                dismiss(r["sid"]); last_scan = 0
                return f"red pill: SIGTERM → pid {r['pid']} · row hidden"
            except Exception as e:
                return f"red pill failed: {e}"

        def label(r):
            return f"{r['repo']} · {r['task'] or r.get('title') or 'session'}"

        while True:
            now = time.time()
            frame = int(now)   # 1 fps animation clock, whatever the input poll rate
            if now - last_scan > REFRESH_S:
                p = load_prefs()                      # live: `m` in another fleet mutes this one too
                SOUND, NOTIFY, RING = p["sound"], p["notify"], p["ring"]
                all_rows = discover()
                if demo:
                    all_rows = demo_rows() + all_rows
                fresh, rung = due_rings(all_rows, rung, now)
                fresh = fresh if last_scan else []    # first scan: whatever rings already is old news
                fresh = [r for r in fresh if not ((NOTIFY or SOUND) and looking_at(r))]  # you're on it already
                for r in fresh:
                    if NOTIFY:
                        notify(label(r), r["now"], r["sid"])
                if fresh:
                    say(f"Wake up, Neo…  {label(fresh[0])} needs you." if THEME["eggs"] != "quiet" else f"{label(fresh[0])} needs you.", 5)
                    if SOUND:
                        ring_sound()                  # once, however many rang together
                new_hot = hot_rows(all_rows)
                for sid in new_hot - hot_seen:
                    r = next(x for x in all_rows if x["sid"] == sid)
                    if last_scan:
                        say(f"context {int(r['ctx_pct'])}% on {label(r)}: /compact before it eats the budget.", 6)
                        if NOTIFY:
                            notify(label(r), f"context {int(r['ctx_pct'])}%: /compact", r["sid"])
                hot_seen = new_hot            # drops below the line (after a /compact) re-arms the alert
                new_ship = {r["sid"] for r in all_rows if r["shipped"]}
                for sid in new_ship - shipped:
                    if last_scan:
                        burst[sid] = now + 1.2
                        if THEME["eggs"] != "quiet":
                            say("He is The One.", 4)
                shipped = new_ship
                rows = ws_rows(all_rows, ws, filt, folded, hidden_repos, SHOW_HIDDEN)
                if pending_sel_sid:
                    sel = next((i for i, rr in enumerate(rows) if rr["sid"] == pending_sel_sid), sel)
                    pending_sel_sid = None
                sel = min(sel, max(0, len(rows) - 1))
                last_scan = now
            burst = {k: v for k, v in burst.items() if v > now}
            if toast and now > toast_until:
                toast = ""
            h, w = scr.getmaxyx()
            if now - last_full > FULL_REPAINT_S:
                prev = None; last_full = now
            A = attrs()
            hot, hot_key, span = set(), (), None
            if manual:
                painted = [(fit(ln, w - 1), A["hdr"] if y == 0 else 0)
                           for y, ln in enumerate(MANUAL.strip("\n").split("\n")[: h - 1])]
            else:
                if prompt_mode:
                    shown_toast = f"task in {prompt_row['repo']} {G['cur']} {prompt_buf}{G['cursor']}   {'⏎' if not is_ascii() else 'enter'} next · esc cancels"
                elif menu_mode:
                    shown_toast = f"spawn in {prompt_row['repo']} {G['cur']} \"{prompt_buf or '(empty: bare claude)'}\"   p plain · a /anderson:start · A /anderson:auto · esc cancels"
                else:
                    shown_toast = confirm or toast
                lines = render(rows, w - 1, sel, frame, filt if filt_mode else "", shown_toast, set(burst), now, height=h - 1, ws=ws, all_rows=all_rows)
                painted = []
                span = ctx_span(w - 1)
                win_off, win_n = _row_window(rows, max(40, w - 1), filt if filt_mode else "", h - 1, sel)
                top = next((i for i, (k, _) in enumerate(lines) if k == "colhdr"), 2) + 1   # first row's line
                for y, (kind, ln) in enumerate(lines[: h - 1]):
                    a = A.get(kind, 0)
                    if kind == "ring" and THEME.get("pulse") and frame % 2:
                        a = col(THEME["ring"]) | DIM          # breathe, once a second
                    if kind == "quote" and confirm:
                        a = col("red") | BOLD
                    if kind == "quote" and (prompt_mode or menu_mode):
                        a = col(THEME["accent"]) | BOLD | REV   # typing has to be findable, not a dim quote
                    painted.append((ln, a))
                    if span and top <= y < top + win_n and kind != "burst":
                        r = rows[win_off + (y - top)]
                        if r["ctx_pct"] is not None and r["ctx_pct"] >= HOT_CTX and r["status"] != "sentinel":
                            hot.add(y)
                hot_key = tuple(sorted(hot))
            key = ((h, w), painted, hot_key)
            if key != prev:                                 # repaint only the lines that changed
                full = prev is None or prev[0] != (h, w)
                if full:
                    scr.erase(); scr.redrawwin()        # redrawwin: resend every cell, even ones curses believes are on screen
                old = prev[1] if not full else []
                for y, (ln, a) in enumerate(painted):
                    if y < len(old) and old[y] == (ln, a) and (y in hot) == (prev and y in prev[2]):
                        continue
                    try:
                        scr.addstr(y, 0, ln, a)
                        if y in hot and span:
                            i0 = cell_index(ln, span[0]); i1 = cell_index(ln, span[0] + span[1])
                            scr.addstr(y, span[0], ln[i0:i1], col("red") | BOLD | (REV if a & REV else 0))
                    except curses.error:
                        pass
                for y in range(len(painted), len(old) if not full else h - 1):
                    try:
                        scr.move(y, 0); scr.clrtoeol()
                    except curses.error:
                        pass
                scr.refresh()
                prev = key
            try:
                k = scr.getch()
            except KeyboardInterrupt:
                return
            if k == -1:
                continue
            if k == curses.KEY_RESIZE or k == 12:       # resize, or ctrl-L: redraw everything now
                prev = None; last_full = now; continue
            if manual:
                manual = False; continue
            if prompt_mode:
                if k == 27:
                    prompt_mode, prompt_row, prompt_buf = False, None, ""
                elif k in (10, 13, curses.KEY_ENTER):
                    prompt_mode, menu_mode = False, True
                elif k in (curses.KEY_BACKSPACE, 127, 8):
                    prompt_buf = prompt_buf[:-1]
                elif 32 <= k < 127:
                    prompt_buf += chr(k)
                continue
            if menu_mode:
                if k == 27:
                    menu_mode, prompt_row, prompt_buf = False, None, ""
                elif k in (ord("p"), ord("a"), ord("A")):
                    say(launch_agent(prompt_row, prompt_buf, chr(k)), 6)
                    menu_mode, prompt_row, prompt_buf = False, None, ""
                continue
            if confirm:
                say(confirm_do(), 8) if k in (ord("y"), ord("Y")) else say("blue sky. nothing happened.")
                confirm = confirm_do = None; continue
            if filt_mode:
                if k == 27:
                    filt, filt_mode = "", False
                elif k in (10, 13, curses.KEY_ENTER):
                    filt_mode = False
                elif k in (curses.KEY_BACKSPACE, 127, 8):
                    filt = filt[:-1]
                elif 32 <= k < 127:
                    filt += chr(k)
                last_scan = 0
                continue
            r = rows[sel] if rows else None
            is_sess = bool(r) and not r.get("kind")
            if k in (ord("q"), 27):
                return
            if k in (curses.KEY_DOWN, ord("j")):
                sel = min(sel + 1, max(0, len(rows) - 1))
            elif k in (curses.KEY_UP, ord("k")):
                sel = max(sel - 1, 0)
            elif k in (10, 13, curses.KEY_ENTER):
                if r:
                    say(activate(r), 6)
            elif ord("1") <= k <= ord("9"):
                if k - ord("1") < len(rows):
                    sel = k - ord("1"); say(activate(rows[sel]), 6)
            elif k == ord("N"):
                say(spawn_into(r) if r else "nothing to spawn into: no repos under this workspace.")
            elif k == ord("o"):
                if is_sess:
                    say(view_gate(r, scr), 4); prev = None; last_full = now
            elif k == ord("w"):
                ringing = [x for x in all_rows if x["status"] == "ring" and not x.get("hidden")]
                if ringing:
                    filt = ""; pending_sel_sid = min(ringing, key=lambda x: x.get("since") or now)["sid"]; last_scan = 0
                    say("follow the white rabbit.")
                else:
                    say("no rabbit. nobody is ringing.")
            elif k == ord("r"):
                if is_sess:
                    confirm = f"red pill: kill {label(r)} ?  How far down does the rabbit hole go? [y/N]"
                    confirm_do = lambda r=r: kill_row(r)
            elif k == ord("b"):
                if r and r.get("kind") == "repo":
                    name = r["repo"]
                    if r.get("hidden"):
                        hidden_repos = {h for h in hidden_repos if not hides(h, name)}; say(f"{name} back in the list.")
                    else:
                        hidden_repos.add(name); say(f"{name} hidden from the repo list.  h shows hidden", 5)
                    save_ws_prefs(ws, hidden=sorted(hidden_repos)); last_scan = 0
                elif is_sess and r.get("hidden"):
                    unhide(r["sid"]); last_scan = 0
                    say("row back in the list.")
                elif is_sess:
                    dismiss(r["sid"], clean=r["status"] == "sentinel"); last_scan = 0
                    live = "" if r["status"] == "sentinel" else " (the session keeps running)"
                    say(f"blue pill: row hidden{live}.  h shows hidden rows", 5)
            elif k == ord("h"):
                SHOW_HIDDEN = not SHOW_HIDDEN; last_scan = 0
                say(f"hidden rows and repos shown ({G['hid']} dim) · b on one brings it back" if SHOW_HIDDEN else "hidden rows hidden.", 5)
            elif k == ord(" "):
                toggle_fold()
            elif k == ord("m"):
                SOUND = not SOUND; save_prefs(sound=SOUND)
                if SOUND:
                    say(f"sound on: '{RING}' rings when a session waits on you (every fleet you have open).", 6)
                    ring_sound()
                else:
                    say("sound off, in every fleet you have open.")
            elif k == ord("/"):
                filt_mode = True; filt = ""
            elif k == ord("?"):
                manual = True

    curses.wrapper(app)
    try:
        sys.stdout.write("\033]2;\007"); sys.stdout.flush()      # hand the tab title back to the shell
    except Exception:
        pass


def boot(scr, curses, col):
    """Digital rain resolving into the sigil, 'Loading anderson…' and one rotating line.
    ~1.8s total; --no-intro skips it. Rain is drawn once per 80ms but the centre block is
    stable, so the eye has somewhere to rest."""
    line = boot_line()
    accent = col(THEME["hdr"])
    t0 = time.time()
    rain_until, hold_until = t0 + 0.7, t0 + 1.8
    seed_chars = "01·10 1 0" if not is_ascii() else "01.10 1 0"
    while time.time() < hold_until:
        h, w = scr.getmaxyx()
        scr.erase()
        if time.time() < rain_until:
            for y in range(h - 1):
                ln = "".join(random.choice(seed_chars) if random.random() < 0.18 else " " for _ in range(w - 1))
                try:
                    scr.addstr(y, 0, ln, accent | curses.A_DIM)
                except curses.error:
                    pass
        cy = max(1, h // 2 - 2)
        block = [f"{G['eyes']}  A N D E R S O N", "", "Loading anderson…", f"\"{line}\""]
        for i, txt in enumerate(block):
            x = max(0, (w - dw(txt)) // 2)
            try:
                scr.addstr(cy + i, 0, " " * (w - 1))
                scr.addstr(cy + i, x, fit(txt, min(dw(txt), w - 1 - x)),
                           accent | (curses.A_BOLD if i in (0, 2) else curses.A_DIM))
            except curses.error:
                pass
        scr.refresh()
        time.sleep(0.08)
    scr.erase(); scr.refresh()


def _dev_tty(t):
    t = (t or "").strip()
    if not t or t in ("??", "-", "?"):
        return None
    return t if t.startswith("/dev/") else f"/dev/{t}"


def _tty_of(pid):
    try:
        r = subprocess.run(["ps", "-o", "tty=", "-p", str(pid)], capture_output=True, text=True, timeout=3)
        return _dev_tty(r.stdout)
    except Exception:
        return None


# iTerm2 / Terminal.app: find the tab by tty, and activate only on a hit. Activating first pulled
# a terminal app you were not even using to the front, just to search it.
FOCUS_ITERM = """tell application "iTerm2"
  repeat with w in windows
    repeat with t in tabs of w
      repeat with s in sessions of t
        if tty of s is "{tty}" then
          activate
          select s
          select t
          set index of w to 1
          return "ok"
        end if
      end repeat
    end repeat
  end repeat
end tell
return "miss\""""

FOCUS_TERMINAL = """tell application "Terminal"
  repeat with w in windows
    repeat with t in tabs of w
      if tty of t is "{tty}" then
        activate
        set selected tab of w to t
        set index of w to 1
        return "ok"
      end if
    end repeat
  end repeat
end tell
return "miss\""""


def _wait_focused(tty, secs):
    """Poll until `tty` is the frontmost tab, or `secs` elapse. True as soon as it lands."""
    end = time.time() + secs
    while time.time() < end:
        time.sleep(0.1)
        if _focused_now(tty):
            return True
    return False


def _focus_tty(app, tty):
    """macOS: bring the iTerm2 / Terminal.app tab owning `tty` to the front and check it got there:
    selecting a tab succeeds even when its window stays on another Space, so the frontmost tab is
    the answer, not the AppleScript's "ok". -> "ok", "unraised" (selected, window stayed put) or None."""
    script = (FOCUS_ITERM if app == "iTerm2" else FOCUS_TERMINAL).replace("{tty}", tty)
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
    except Exception:
        return None
    if r.stdout.strip() != "ok":
        return None
    # a same-Space raise lands in ~0.15s; crossing Spaces plays a ~1s animation first
    return "ok" if _wait_focused(tty, 2.0) else "unraised"


TERMINAL_BUNDLES = {"com.apple.Terminal", "com.googlecode.iterm2", "dev.warp.Warp-Stable", "com.mitchellh.ghostty",
                    "com.github.wez.wezterm", "net.kovidgoyal.kitty"}


def _front_app():
    """macOS: (bundle id, display name) of the frontmost app, via lsappinfo (no AppleScript, ~10 ms)."""
    try:
        asn = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True, timeout=2).stdout.strip()
        info = subprocess.run(["lsappinfo", "info", "-only", "bundleid", "-only", "name", asn],
                              capture_output=True, text=True, timeout=2).stdout
        bid = re.search(r'"CFBundleIdentifier"="([^"]+)"', info)
        name = re.search(r'"LSDisplayName"="([^"]+)"', info)
        return (bid.group(1) if bid else "", name.group(1) if name else "")
    except Exception:
        return ("", "")


def _selected_tty(bundle):
    """The tty shown in the frontmost Terminal.app / iTerm2 tab, or None."""
    scripts = {"com.apple.Terminal": 'tell application "Terminal" to get tty of selected tab of front window',
               "com.googlecode.iterm2": 'tell application "iTerm2" to get tty of current session of current window'}
    if bundle not in scripts:
        return None
    try:
        r = subprocess.run(["osascript", "-e", scripts[bundle]], capture_output=True, text=True, timeout=3)
        return _dev_tty(r.stdout)
    except Exception:
        return None


def _focused_now(tty):
    """True when `tty` is the tty of the Terminal.app / iTerm2 tab in front of the human right now."""
    try:
        bid, _ = _front_app()
        return bool(bid) and _selected_tty(bid) == tty
    except Exception:
        return False


def looking_at(r):
    """True when the session's own terminal tab is what the human is looking at right now, so a
    banner and a ring would only repeat what is in front of them. Best effort, False on any doubt.
    ponytail: a tmux pane counts as watched when it is the active pane of an attached session and a
    terminal app is frontmost; which terminal window hosts that tmux client is not checked."""
    if sys.platform != "darwin" or not r.get("pid"):
        return False
    try:
        bid, name = _front_app()
        if not bid:
            return False
        if r.get("tmux_pane"):
            if bid not in TERMINAL_BUNDLES:
                return False
            flags = subprocess.run(["tmux", "display", "-p", "-t", r["tmux_pane"],
                                    "#{pane_active}#{window_active}#{session_attached}"],
                                   capture_output=True, text=True, timeout=2).stdout.strip()
            return flags.startswith("11") and flags[2:3] not in ("", "0")
        app = _owner_app(r["pid"])
        if not app:
            return False
        if app[0] == "Ghostty":
            # Ghostty in front is not enough (fleet's own tab is Ghostty too): its focused tab must be this one
            if bid != "com.mitchellh.ghostty":
                return False
            tid, _ = ghostty_tid(r, app[2])
            front = _jxa(f"{_ghostty_app(app[2])}.frontWindow().selectedTab().focusedTerminal().id()").stdout.strip()
            return bool(tid) and front == tid
        if app[0] in ("iTerm", "iTerm2", "Terminal"):
            return _selected_tty(bid) == _tty_of(r["pid"])
        return app[0].lower() in (name.lower(), bid.lower().rsplit(".", 1)[-1])   # IDE terminal: the IDE is in front
    except Exception:
        return False


# JXA, not AppleScript: `tell application "Ghostty"` talks to whichever instance macOS picks, and a
# second one (a stray `ghostty -e ...` an agent launched) then hides every tab of the real one.
# Application(<pid>) addresses the instance that owns the session.
def _ghostty_app(app_pid):
    return f"Application({int(app_pid)})" if app_pid else 'Application("Ghostty")'


def _jxa(script):
    return subprocess.run(["osascript", "-l", "JavaScript", "-e", script], capture_output=True, text=True, timeout=5)


def ghostty_pick(listing, cwd):
    """The Ghostty terminal id to focus for a session in `cwd`, from _ghostty_list()'s output,
    or (None, why). The fallback when the tty mark fails: Ghostty has no tty in its dictionary, so
    the tab is found by working directory; two tabs in one directory are told apart by the claude
    title (a spinner glyph, or "Claude Code"), which a bare shell prompt does not carry."""
    want = os.path.realpath(cwd or "")
    hits = []
    for ln in (listing or "").splitlines():
        parts = ln.split("\t", 2)
        if len(parts) == 3 and parts[1] and os.path.realpath(parts[1]) == want:
            hits.append(parts)
    if len(hits) > 1:
        claude = [h for h in hits if h[2].strip() == "Claude Code" or re.match(r"^[^\w\s~/]", h[2])]
        hits = claude or hits
    if len(hits) == 1:
        return hits[0][0], None
    return None, (f"{len(hits)} tabs in {cwd}, can't tell which" if hits else f"no tab in {cwd}")


def _ghostty_list(app_pid=None):
    """One `id<TAB>working directory<TAB>name` line per Ghostty terminal."""
    return _jxa(f'var a = {_ghostty_app(app_pid)}; a.terminals().map(t => [t.id(), t.workingDirectory(), t.name()].join("\\t")).join("\\n")').stdout


def _tty_title(tty, title):
    """Set the title of the terminal showing `tty` (OSC 2), as if the program on it had."""
    title = re.sub(r"[\x00-\x1f\x7f]", "", title)
    fd = os.open(tty, os.O_WRONLY | os.O_NOCTTY)
    try:
        os.write(fd, f"\033]2;{title}\007".encode())
    finally:
        os.close(fd)


def _ghostty_mark(tty, before, app_pid=None):
    """The Ghostty terminal id showing `tty`, or None. Ghostty's dictionary has no tty, but a title
    written to the tty shows up as that terminal's `name`: write a unique one, find it, then put
    the old title back. Exact however many tabs share a directory."""
    names = {p[0]: p[2] for p in (ln.split("\t", 2) for ln in (before or "").splitlines()) if len(p) == 3}
    mark = f"fleet-{os.getpid()}-{time.time_ns()}"
    try:
        _tty_title(tty, mark)
    except OSError:
        return None
    for _ in range(10):                                   # Ghostty applies it in ~0.1s
        for ln in _ghostty_list(app_pid).splitlines():
            p = ln.split("\t", 2)
            if len(p) == 3 and p[2].strip() == mark:
                _tty_title(tty, names.get(p[0], "Claude Code"))
                return p[0]
        time.sleep(0.1)
    _tty_title(tty, "")                                   # not a Ghostty tty: an empty title resets it
    return None


_GHOSTTY_TID = {}    # pid -> Ghostty terminal id, found by tty mark: exact, and stable for the tab's life


def ghostty_tid(r, app_pid):
    """(terminal id, None) of the Ghostty tab a session runs in, or (None, why). By tty first (exact,
    cached per pid while the tab lives, since each lookup flashes the title), else by the directory
    claude was launched from: the live cwd follows every `cd` the session makes, the tab's does not."""
    listing = _ghostty_list(app_pid)
    pid = r.get("pid")
    if pid in _GHOSTTY_TID and any(ln.startswith(_GHOSTTY_TID[pid] + "\t") for ln in listing.splitlines()):
        return _GHOSTTY_TID[pid], None
    tty = _tty_of(pid) if pid else None
    tid = _ghostty_mark(tty, listing, app_pid) if tty else None
    if tid:
        _GHOSTTY_TID[pid] = tid
        return tid, None
    cwd = r.get("start_cwd") or r.get("cwd")
    return ghostty_pick(listing, cwd) if cwd else (None, "no tty and no directory to find its tab by")


def _owner_app(pid):
    """macOS: (name, .app path, pid) of the app that owns this process (WebStorm, VS Code, Ghostty...),
    via the ppid chain. The pid tells two running instances of one app apart."""
    try:
        seen = 0
        while pid and int(pid) > 1 and seen < 32:
            r = subprocess.run(["ps", "-o", "ppid=,command=", "-p", str(pid)], capture_output=True, text=True, timeout=3)
            parts = r.stdout.strip().split(None, 1)
            if len(parts) < 2:
                return None
            m = re.search(r"(/[^\0]*?/([^/]+)\.app)/Contents/MacOS/", parts[1])
            if m:
                return m.group(2), m.group(1), int(pid)
            pid = parts[0]; seen += 1
    except Exception:
        pass
    return None


def focus_owner(r):
    """macOS: bring the terminal tab running r["pid"] to the front, whichever app owns it.
    -> "Operator." or why not."""
    app = _owner_app(r["pid"])
    if not app:
        return "can't tell which app runs that session (not under a macOS app)."
    name, path, app_pid = app
    try:
        if name == "Ghostty":
            tid, why = ghostty_tid(r, app_pid)
            if not tid:
                return f"Ghostty: {why}"
            ok = _jxa(f'var a = {_ghostty_app(app_pid)}; a.activate(); a.focus(a.terminals.byId({json.dumps(tid)})); "ok"')
            return "Operator." if ok.returncode == 0 else f"Ghostty: {ok.stderr.strip() or 'focus failed'}"
        if name in ("iTerm", "iTerm2", "Terminal"):
            tty = _tty_of(r["pid"])
            landed = _focus_tty("iTerm2" if name.startswith("iTerm") else "Terminal", tty) if tty else None
            if landed == "ok":
                return "Operator."
            if landed == "unraised":
                return ("that tab is selected but its window stayed on another Space. fix it once: "
                        "defaults write com.apple.dock workspaces-auto-swoosh -bool YES; killall Dock")
            return f"no {name} tab shows that session."
        subprocess.run(["open", "-a", path], timeout=5)
        return f"Operator. ({name}: app in front; its terminal tab can't be picked from outside)"
    except Exception as e:
        return f"jack in failed: {e}"


def jack_in(r):
    """⏎: bring that session's terminal to the front. A sentinel has none left, so it gets a new tab
    resuming it. A tmux session: its pane, shown by whichever terminal is attached (a new tab
    attaches when none is). Else (macOS) the tab of the app that owns the process."""
    if r.get("status") == "sentinel":
        return revive(r)
    pane = r.get("tmux_pane")
    if pane:
        try:
            tm = lambda *a: subprocess.run(["tmux", *a], capture_output=True, text=True, timeout=3).stdout.strip()
            sess = tm("display", "-p", "-t", pane, "#S")
            tm("select-window", "-t", pane); tm("select-pane", "-t", pane)
            if os.environ.get("TMUX") and tm("display", "-p", "#S") == sess:
                return "Operator. (same tmux session as fleet: prefix+l comes back)"
            clients = tm("list-clients", "-t", sess, "-F", "#{client_pid}").split()
            if clients and sys.platform == "darwin":
                return focus_owner({"pid": int(clients[0])})
            if sys.platform == "darwin":
                return new_terminal(f"tmux attach -t {shlex_quote(sess)}", verb="attached")
            return f"pane {r.get('tmux_addr') or pane} selected. attach with: tmux attach -t {sess}"
        except Exception as e:
            return f"jack in failed: {e}"
    if sys.platform != "darwin":
        return "no tmux pane for that session. start it inside tmux to jack in."
    if not r.get("pid"):
        return "no process known for that session yet."
    return focus_owner(r)


def focus_fleet():
    """`fleet --focus`: bring the running fleet's own tab back to the front, from anywhere. Bind it to a
    hotkey; it is the way back after a jack in. Finds a fleet run in place (not one inside tmux)."""
    try:
        tty, pid = open(os.path.join(FLEET_DIR, "fleet.tty")).read().split()
    except Exception:
        return "no running fleet found."
    if not alive(pid):
        return "fleet is not running."
    return focus_owner({"pid": int(pid)})


# ─────────────────────────────────────────────────────────────────── main
def selftest():
    random.seed(7)
    words = ["fashion-webapp-2", "ai-shoot-service", "claude-loop", "x", "a-very-long-repository-name-that-goes-on",
             "ar-2270-sku-images-lightbox", "déjà-vu-tâche-éè", "日本語のタスク", "remove-db-triggers", ""]
    stages = list(PERSONA) + [""]
    fails = 0
    # repo-section rows, CJK and overlong names, mixed into the same width fuzz as the session rows
    tree_words = ["autoretouch", "日本語のタスク", "a-very-long-repository-name-that-goes-on-and-on-and-on", "x"]
    tree_rows_fuzz = [{**_WS_BASE, "sid": "section:repos", "kind": "section", "repo": "repos (4)", "now": "N spawns"}]
    tree_rows_fuzz += [{**repo_target(f"/tmp/ws/{nm}", nm), "now": "2 agents"} for nm in tree_words]
    for theme in THEME_ORDER:
        set_theme(theme)
        for width in list(range(60, 221, 7)) + [40, 300]:
            rows = list(tree_rows_fuzz)
            for i in range(12):
                st = random.choice(stages)
                gk, persona, ms, mood = PERSONA.get(st, ("none", "T. ANDERSON", "", ""))
                rows.append(dict(sid=f"s{i}", pid=None, cwd="", root="", repo=random.choice(words), task=random.choice(words),
                                 stage=st, persona=persona, pglyph=PGLYPH[gk], mood=mood, model=ms.format(**review_effort(None)) or "opus",
                                 iteration=str(random.randint(0, 3)), max_iter="2", plan_verdict="ship", diff_verdict="pending",
                                 dejavu=random.random() < .5, status=random.choice(["ring", "work", "sentinel"]),
                                 now=random.choice([f"{G['run']} Bash pytest -q tests/orders/… very long command line", f"{G['ring']} ring"]),
                                 text="x" * random.randint(0, 300), cost=random.choice([None, 0.5, 123.456]),
                                 ctx_pct=random.choice([None, 0, 61, 100]), lines=(1, 2), start=time.time() - 100,
                                 last_seen=time.time(), tmux_pane=None, tmux_addr=None, shipped=False, hb_ts=None))
            for lines in (render(rows, width, sel=3, frame=2, toast="Wake up, Neo…", burst={"s1"}),
                          render(rows, width, sel=3, frame=2, height=50), render([], width, height=50),
                          render(rows, width, filt="abc")):
                for kind, ln in lines:
                    if dw(ln) != max(40, width):
                        fails += 1
                        print(f"MISALIGNED theme={theme} width={width} kind={kind} got={dw(ln)}: {ln!r}")
    set_theme("matrix")
    assert dw(fit("日本語", 4)) == 4
    assert dw(fit("éx", 3)) == 3
    # viewport: more rows than the terminal has lines -> the footer and the selected row must
    # still be on screen, not truncated off the bottom by run_tui's lines[:h-1]
    big = [dict(sid=f"b{i}", pid=None, cwd="", root="", repo=f"repo{i}", task="t", stage="implement",
                persona="NEO", pglyph=PGLYPH["neo"], mood="action", model="sonnet/medium", iteration="0",
                max_iter="2", plan_verdict="ship", diff_verdict="pending", dejavu=False, status="work",
                now=f"{G['run']} working", text="", cost=0.1, ctx_pct=10, lines=(1, 1), start=time.time(),
                last_seen=time.time(), tmux_pane=None, tmux_addr=None, shipped=False, hb_ts=None)
           for i in range(40)]
    vlines = render(big, 100, sel=37, height=24)
    if len(vlines) > 24:
        fails += 1; print(f"VIEWPORT: {len(vlines)} lines emitted for height=24")
    if vlines[-1][0] != "foot":
        fails += 1; print("VIEWPORT: footer is not the last line")
    if not any(kind.endswith("_sel") for kind, _ in vlines):
        fails += 1; print("VIEWPORT: selected row not painted")
    print("alignment selftest:", "FAIL" if fails else "ok", f"({fails} bad lines, {len(THEME_ORDER)} themes)")
    return 1 if fails else 0


def main(argv):
    args = argv[1:]
    if "--focus" in args:
        print(focus_fleet())
        return 0
    if "--jack" in args and args.index("--jack") + 1 < len(args):
        sid = args[args.index("--jack") + 1]
        r = next((x for x in discover(hidden=True) if x["sid"] == sid), None)
        print(jack_in(r) if r else f"no session {sid}")
        return 0
    if "--ascii" in args or (os.environ.get("LANG", "").lower()[:2] in ("ja", "zh", "ko") and "--unicode" not in args):
        use_ascii()
    global PLAIN
    prefs = load_prefs()
    theme = prefs["theme"]
    for a in args:
        if a.startswith("--theme="):
            theme = a.split("=", 1)[1]
    if "--theme" in args and args.index("--theme") + 1 < len(args):
        theme = args[args.index("--theme") + 1]
    if "--plain" in args:
        prefs["plain"] = True
    if "--lingo" in args:
        prefs["plain"] = False
    if "--calm" in args:
        prefs["calm"] = True
    if "--motion" in args:
        prefs["calm"] = False
    if "--cost" in args:
        prefs["cost"] = True
    if "--no-cost" in args:
        prefs["cost"] = False
    if "--notify" in args:
        prefs["notify"] = True
    if "--no-notify" in args:
        prefs["notify"] = False
    if "--sound" in args:
        prefs["sound"] = True
    if "--no-sound" in args:
        prefs["sound"] = False
    if "--ring" in args and len(args) > args.index("--ring") + 1:
        prefs["ring"] = args[args.index("--ring") + 1]; prefs["sound"] = True
    for a in args:
        if a.startswith("--ring="):
            prefs["ring"] = a.split("=", 1)[1]; prefs["sound"] = True
    global SHOW_COST, NOTIFY, SOUND, RING
    SHOW_COST = prefs["cost"]; NOTIFY = prefs["notify"]; SOUND = prefs["sound"]; RING = prefs["ring"]
    if "--rings" in args:
        for n in sound_names():
            print(f"  {n:8} {'◂ current' if n == RING else ''}  {sound_file(n)}")
        print("  hear one: fleet --play NAME   ·   pick: fleet --ring NAME")
        return 0
    if "--ping" in args:
        print("sending a test banner through every channel; note which ones you actually see:")
        if sys.platform == "darwin":
            tn = shutil.which("terminal-notifier")
            if tn:
                r = subprocess.run([tn, "-title", "THE OPERATOR", "-subtitle", "ping 1/2", "-message", "terminal-notifier channel",
                                    "-group", "anderson-fleet-ping"], capture_output=True, text=True)
                print(f"  1. terminal-notifier   rc {r.returncode}  {r.stderr.strip() or r.stdout.strip() or 'no output'}")
                print("     not shown? System Settings › Notifications › terminal-notifier: Allow Notifications ON, style Banners or Alerts")
            else:
                print("  1. terminal-notifier   not installed (brew install terminal-notifier); it is the reliable channel")
            r = subprocess.run(["osascript", "-e", 'display notification "osascript channel" with title "THE OPERATOR" subtitle "ping 2/2"'],
                               capture_output=True, text=True, timeout=10)
            print(f"  2. osascript           rc {r.returncode}  {r.stderr.strip() or 'no output'}")
            print("     not shown? System Settings › Notifications › Script Editor: Allow Notifications ON")
            print("  also: a Focus mode (Do Not Disturb) hides both; the fleet ring sound is independent of all this")
        elif shutil.which("notify-send"):
            r = subprocess.run(["notify-send", "THE OPERATOR", "ping"], capture_output=True, text=True)
            print(f"  notify-send rc {r.returncode} {r.stderr.strip()}")
        else:
            print("  no notification channel on this platform")
        return 0
    if "--play" in args:
        i = args.index("--play")
        name = args[i + 1] if len(args) > i + 1 and not args[i + 1].startswith("-") else RING
        if name != "all":
            names = [name]
        else:
            names = sound_names()
        for n in names:
            f = sound_file(n)
            if not f:
                print(f"no sound named '{n}'  (fleet --rings lists them)"); return 1
            print(f"  ▶ {n}")
            for player in (["afplay"], ["paplay"], ["aplay", "-q"]):
                if shutil.which(player[0]):
                    subprocess.run(player + [f]); break
            else:
                print("no player found (afplay / paplay / aplay)"); return 1
        return 0
    PLAIN = prefs["plain"]
    if theme in THEMES and "--selftest" not in args and "--once" not in args:
        save_prefs(theme=theme, plain=prefs["plain"], calm=prefs["calm"], cost=prefs["cost"], notify=prefs["notify"], sound=prefs["sound"], ring=prefs["ring"])
    set_theme(theme or "matrix", calm=prefs["calm"])
    if "--themes" in args:
        for n, t in THEMES.items():
            print(f"  {n:16} {t['desc']}")
        return
    if "--selftest" in args:
        sys.exit(selftest())
    width = shutil.get_terminal_size((120, 30)).columns
    for a in args:
        if a.startswith("--width="):
            width = int(a.split("=", 1)[1])
    if "--once" in args or not sys.stdout.isatty():
        all_rows = discover()
        if "--demo" in args:
            all_rows = demo_rows() + all_rows
        ws = workspace_root(os.getcwd())
        wp = ws_prefs(ws)
        rows = ws_rows(all_rows, ws, "", wp["folded"], set(wp["hidden"]))
        for _, ln in render(rows, width, sel=0, frame=int(time.time()) % 4, ws=ws, all_rows=all_rows):
            print(ln)
        return
    run_tui(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
