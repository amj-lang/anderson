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
    python3 bin/fleet.py --zoom 16     # Terminal.app: font size while fleet runs (saved; --no-zoom clears)
    python3 bin/fleet.py --cost        # show the api$ column on a subscription (saved; --no-cost hides)
    python3 bin/fleet.py --notify      # desktop notification when a session starts ringing (saved)
    python3 bin/fleet.py --sound       # the ring plays when a session starts waiting (saved; --no-sound)
    python3 bin/fleet.py --ring snare  # pick the ring sound (--rings lists them; `s` cycles in the TUI)
    python3 bin/fleet.py --play all    # audition every bundled sound in a row (--play NAME for one)
    python3 bin/fleet.py --ping        # test the desktop banner through every channel, with where to look if none shows
    python3 bin/fleet.py --editor code # what opens plan.md / audit.md on `o` or at a gate (saved)

Data, richest first, each optional (the view degrades, never breaks):
  ~/.claude/fleet/<sid>.status.json   heartbeat from bin/heartbeat.py (statusline): $, ctx, model
  ~/.claude/fleet/<sid>.event.json    hooks/fleet_event.py: waiting-on-you vs working
  ~/.claude/projects/<cwd>/<sid>.jsonl transcript tail: last tool, last words, ctx tokens
  <repo>/feature-research/*/state.md  anderson stage/verdicts/iteration -> persona
  ps + lsof + tmux                    sessions with no hooks at all, and the pane to jack into

Keys: ↑↓/jk tune · ⏎ jack in (tmux) · w white rabbit (oldest ring) · r kill (row hidden too)
      b hide the row (process untouched) · h show hidden · / filter · t theme · p wording · ? manual · q
Prefs (theme, wording, motion) persist in ~/.claude/fleet/prefs.json.
"""
import glob, json, os, random, re, shutil, signal, subprocess, sys, time, unicodedata

FLEET_DIR = os.path.expanduser(os.environ.get("ANDERSON_FLEET_DIR", "~/.claude/fleet"))
PROJECTS = os.path.expanduser("~/.claude/projects")
HERE = os.path.dirname(os.path.abspath(__file__))
STALE_S = 24 * 3600          # forget sessions with no sign of life for a day
CTX_WINDOW = 200_000         # fallback when the heartbeat has no context_window_size
REFRESH_S = 2.0
FULL_REPAINT_S = 10.0        # erase + redraw the whole screen this often; the diff repaint cannot see what the terminal lost

# ──────────────────────────────────────────────────────────────────────── glyphs
UNI = dict(eyes="⌐■-■", cur="▸", ring="☎", dead="✝", loop="⟲", run="▶", ship="★", hid="◌",
           bar="▓", trk="░", rule="─", ell="…", det="▍",
           rain=("0·1 1", "1 0·1", " 1·10", "1·0 1"), raincol="01·10")
ASCII = dict(eyes="[-_-]", cur=">", ring="!", dead="x", loop="~", run=">", ship="*", hid="h",
             bar="#", trk=".", rule="-", ell="~", det="|",
             rain=("0.1 1", "1 0.1", " 1.10", "1.0 1"), raincol="01.10")
G = dict(UNI)

# stage -> (glyph key, persona, model/effort, quote mood)
PERSONA = {
    "plan":        ("arch",  "ARCHITECT",    "opus/high",     "design"),
    "grill":       ("grill", "INTERROGATOR", "you",           "insight"),
    "plan_review": ("orac",  "ORACLE",       "{rm}/xhigh",    "insight"),
    "implement":   ("neo",   "NEO",          "sonnet/medium", "action"),
    "diff_review": ("smith", "AGENT SMITH",  "{rm}/high",     "adversary"),
    "done":        ("one",   "THE ONE",      "shipped",       "mentor"),
    "aborted":     ("smith", "AGENT SMITH",  "aborted",       "adversary"),
}
PGLYPH_UNI = dict(arch="▲", grill="◇", orac="◎", neo="●", smith="▣", one="★", none="○")
PGLYPH_ASCII = dict(arch="A", grill="?", orac="O", neo="N", smith="S", one="*", none="o")
PGLYPH = dict(PGLYPH_UNI)


def use_ascii():
    G.clear(); G.update(ASCII); PGLYPH.clear(); PGLYPH.update(PGLYPH_ASCII)


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
        return "—" if G is not ASCII else "-"
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
        if os.path.isdir(os.path.join(d, "feature-research")) or os.path.isdir(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    return cwd


def anderson_state(root):
    """Most recently touched feature-research/*/state.md under root, parsed leniently."""
    if not root:
        return {}
    paths = glob.glob(os.path.join(root, "feature-research", "*", "state.md"))
    if not paths:
        return {}
    p = max(paths, key=lambda x: os.path.getmtime(x))
    try:
        t = open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return {}
    st = {k: field(t, k) for k in
          ("task", "stage", "iteration", "max_iterations", "plan_verdict", "diff_verdict", "review_model", "branch", "gate")}
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
               title="", branch=None)
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
        if d.get("type") == "summary" and d.get("summary") and not out["title"]:
            out["title"] = str(d["summary"]).strip()          # /resume title, when Claude Code wrote one
        if d.get("type") == "user" and not d.get("isSidechain") and not d.get("isMeta") and not out["title"]:
            c = (d.get("message") or {}).get("content")
            txt = c if isinstance(c, str) else " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text") if isinstance(c, list) else ""
            txt = txt.strip()
            if txt and not txt.startswith("<"):               # skip slash-command / caveat wrappers
                out["title"] = txt.split("\n")[0][:120]
        if out["start"] and out["title"]:
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
    st = anderson_state(root)
    stage = (st.get("stage") or "").lower()
    if stage in ("ship",):
        stage = "done"
    gk, persona, model_spec, mood = PERSONA.get(stage, ("none", "T. ANDERSON", "", ""))
    rm = (st.get("review_model") or "fable")
    model_spec = model_spec.format(rm=rm)
    if not model_spec:
        model_spec = _short_model(s.get("model") or tr.get("model") or "")
    # status: dead? then hook event if fresher than the transcript, else transcript inference
    pid_alive = alive(s.get("pid"))
    dead = ev.get("ended") or pid_alive is False or s.get("no_proc", False)
    ev_fresh = bool(ev) and (ev.get("ts") or 0) >= (tr.get("ts") or 0) - 1
    tool = tr.get("tool"); arg = tr.get("tool_arg") or ""
    since = max([x for x in (tr.get("ts"), ev.get("ts")) if x] or [0])
    wait = f" {age_str(since)}" if since else ""             # how long it has been waiting on you
    if dead:
        status, now_txt = "sentinel", f"{G['dead']} sentinel"
    elif ev_fresh and ev.get("waiting") is True:
        status = "ring"
        n = (ev.get("notification") or "")
        if "permission" in str(n).lower():
            now_txt = f"{G['ring']} permission {tool or ''}".rstrip() + wait
        else:
            now_txt = f"{G['ring']} ring" + wait
    elif ev_fresh and ev.get("waiting") is False and tr.get("state") != "tool":
        status, now_txt = "work", f"{G['run']} thinking"
    elif tr.get("state") == "idle":
        status, now_txt = "ring", f"{G['ring']} ring" + wait
    elif tr.get("state") == "tool":
        status, now_txt = "work", f"{G['run']} {tool} {arg}".rstrip()
    elif tr.get("state") == "think" and tr.get("ts") and now - tr["ts"] > 15 * 60:
        status, now_txt = "ring", f"{G['ring']} idle" + wait   # interrupted turn: nothing ran for 15 min
    elif tr.get("state") == "think":
        status, now_txt = "work", f"{G['run']} thinking"
    else:
        status, now_txt = "work", f"{G['run']} jacked in"
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
        "plan_verdict": st.get("plan_verdict"), "diff_verdict": st.get("diff_verdict"), "branch": st.get("branch") or tr.get("branch"),
        "gate": (st.get("gate") or "").lower(),
        "dejavu": bool(it and it.isdigit() and int(it) > 0),
        "status": status, "now": now_txt, "text": tr.get("text") or "",
        "cost": s.get("cost_usd"), "ctx_pct": ctx_pct, "ctx_tokens": toks,
        "lines": (s.get("lines_added"), s.get("lines_removed")),
        "start": start, "last_seen": last_seen, "agents": subagents(s.get("transcript_path"), now),
        "tmux_pane": s.get("tmux_pane"), "tmux_addr": s.get("tmux_addr"),
        "shipped": stage == "done", "hb_ts": s.get("hb_ts"),
    }


def _short_model(m):
    m = (m or "").lower().replace("claude-", "")
    for k in ("fable", "opus", "sonnet", "haiku"):
        if k in m:
            return k
    return m[:12]


# ───────────────────────────────────────────────────────────────────── demo
def demo_rows():
    now = time.time()
    base = dict(pid=None, cwd="", root="", plan_verdict="ship", diff_verdict="pending", lines=(212, 48),
                tmux_pane=None, tmux_addr=None, shipped=False, hb_ts=now, last_seen=now, sid="demo")
    mk = lambda **k: {**base, **k}
    st = lambda s: PERSONA[s]
    return [
        mk(sid="demo-1", repo="fashion-webapp-2", task="ar-2270-sku-images-lightbox", stage="diff_review",
           persona=st("diff_review")[1], pglyph=PGLYPH["smith"], mood="adversary", model="fable/high",
           iteration="1", max_iter="2", dejavu=True, status="ring", now=f"{G['ring']} ring",
           text="47 passed, 0 failed. Verdict: fix_first, one unproven criterion.", cost=1.42, ctx_pct=61,
           start=now - 12 * 60, diff_verdict="fix_first"),
        mk(sid="demo-2", repo="ai-shoot-service", task="remove-db-triggers", stage="implement",
           persona=st("implement")[1], pglyph=PGLYPH["neo"], mood="action", model="sonnet/medium",
           iteration="0", max_iter="2", dejavu=False, status="work", now=f"{G['run']} Edit orders.py",
           text="Replacing the trigger with an explicit write in process_order().", cost=0.88, ctx_pct=34,
           start=now - 4 * 60),
        mk(sid="demo-3", repo="claude-loop", task="readbility", stage="grill",
           persona=st("grill")[1], pglyph=PGLYPH["grill"], mood="insight", model="you",
           iteration="0", max_iter="2", dejavu=False, status="ring", now=f"{G['ring']} ring",
           text="Question 3 of 7: should the What block cap at three lines or three sentences?", cost=0.12,
           ctx_pct=9, start=now - 41 * 60),
        mk(sid="demo-4", repo="fashion-webapp-2", task="sku-bulk-upload", stage="plan",
           persona=st("plan")[1], pglyph=PGLYPH["arch"], mood="design", model="opus/high",
           iteration="2", max_iter="2", dejavu=True, status="sentinel", now=f"{G['dead']} sentinel",
           text="", cost=0.31, ctx_pct=None, start=now - 2 * 3600, pid=None),
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
    z = d.get("zoom")
    return {"theme": d.get("theme") or "matrix", "plain": bool(d.get("plain")), "calm": bool(d.get("calm")),
            "zoom": int(z) if isinstance(z, (int, float)) and 6 <= int(z) <= 72 else None,
            "cost": bool(d.get("cost")), "notify": bool(d.get("notify")), "editor": d.get("editor") or None,
            "sound": bool(d.get("sound")), "ring": d.get("ring") or "phone"}


def save_prefs(**kw):
    d = load_prefs(); d.update({k: v for k, v in kw.items() if v is not None or k == "zoom"})
    try:
        os.makedirs(FLEET_DIR, exist_ok=True)
        with open(PREFS_FILE, "w") as f:
            json.dump(d, f)
    except Exception:
        pass
    return d


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
    ("model",   "model",   13,   "l", 140),
    ("now",     "now",     22,   "l", 85),
    ("cost",    "api$",    6,    "r", 100),
    ("ctx",     "ctx",     15,   "l", 120),
    ("ctxp",    "ctx",     4,    "r", 0),      # compact ctx, only when the bar is hidden
    ("age",     "age",     4,    "r", 100),
]
PREFIX = 3   # margin + cursor + space


SHOW_COST = False    # api$ column: on for API-key users (no limits), opt-in on subscriptions (--cost, `$` key)


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
        return G["trk"] * w + "   " + ("—" if G is not ASCII else "-").rjust(1)
    n = max(0, min(w, int(round(pct / 100.0 * w))))
    return G["bar"] * n + G["trk"] * (w - n) + f" {int(pct):3d}%"


def cell(row, key, frame):
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
        return "  " + (SPIN[frame % 4] if G is not ASCII else "|/-\\"[frame % 4])
    if THEME.get("pulse"):
        return "  " + ("·" if frame % 2 else " ")
    return ""


def next_step(r):
    """What the human does next for this row, in one line."""
    st, gate, task = r.get("stage") or "", r.get("gate") or "", r.get("task") or ""
    if r["status"] == "sentinel":
        return "c copies the resume command · b dismisses the row"
    if st == "grill":
        return "answer the interrogation in the session (⏎), it hardens plan.md"
    if st == "plan_review" and gate == "human":
        return f"read plan.md (o) → /anderson:approve-plan {task}  · or say what to change"
    if st == "diff_review" and gate == "human":
        v = r.get("diff_verdict") or ""
        return f"read plan.md + audit.md (o) → /anderson:approve-diff {task}" + (f"  · verdict {v}: /anderson:rework {task}" if v == "fix_first" else "")
    if st == "implement":
        return "NEO is writing code; nothing to do until diff review"
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
    L("who", who + (f" · model {r['model']}" if r.get("model") else ""))
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
    where = r["tmux_addr"] or r["tmux_pane"] or "no tmux pane"
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


def render(rows, width, sel=0, frame=0, filt="", toast="", burst=(), t=None, height=None):
    """Pure: -> list of (kind, line). Every line is exactly `width` cells (see --selftest)."""
    t = time.time() if t is None else t
    W = max(40, width)
    cols = layout(W)
    lines = []
    n_ring = sum(r["status"] == "ring" for r in rows)
    n_hid = sum(bool(r.get("hidden")) for r in rows)
    n_dead = sum(r["status"] == "sentinel" and not r.get("hidden") for r in rows)
    n_live = len(rows) - n_dead - n_hid
    left = f"{G['eyes']}  T H E  O P E R A T O R"
    right = f"{words('fleet')} · {n_live} {words('live')} · {n_ring} {words('ring')} · {n_dead} {words('deads' if n_dead != 1 else 'dead')}{f' · {n_hid} hidden' if n_hid else ''}{header_tail(frame)}"
    lines.append(("hdr", fit(fit(left, max(0, W - dw(right) - 1)) + " " + right, W)))
    lim = usage_limits(bars=True)
    if lim:                                      # the plan's windows: the number to keep an eye on, so it lives up here
        lines.append(("usage_hot" if usage_hot() else "usage", fit(f"{G['det']} {THEME['name']} · {lim}", W)))
    foot = footer(rows, W, filt)
    # tall terminal (16+ free lines after the list and the footer): blank lines around the rules, so it breathes
    airy = bool(height) and height - (len(lines) + len(rows) + 4 + len(foot)) >= 16
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
    for i, r in enumerate(rows):
        cur = G["cur"] if i == sel else " "
        num = str(i + 1) if i < 9 else " "
        if r["sid"] in burst:
            body = "".join(random.choice("01·10 1 0") for _ in range(W - PREFIX))
            kind = "burst"
        else:
            body = "  ".join(fit(cell(r, k, frame), w, a) for k, _, w, a in cols)
            kind = ("hidden" if r.get("hidden") else r["status"]) + ("_sel" if i == sel else "")
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


def footer(rows, W, filt=""):
    """Bottom of the screen: rule, the keys (wrapped, never truncated), then usage on its own line."""
    d = G["det"]
    fleet = sum(r["cost"] or 0 for r in rows)
    lim = usage_limits()
    keys = ("↑↓ tune · 1-9/⏎ jack in · o read plan · O in IDE · w rabbit · 🔴 r kill · 🔵 b hide · 👻 h hidden · c resume · "
            "🔔 n notify · 🔊 m sound · 🎵 s ring · $ cost · +/- zoom · 🔍 / filter · 🎨 t theme · p wording · ? manual · q quit") \
        if G is not ASCII else ("jk tune · 1-9/enter jack in · o read plan · O in IDE · w rabbit · r kill · b hide · h hidden · c resume · "
                                "n notify · m sound · s ring · $ cost · +/- zoom · / filter · t theme · p wording · ? manual · q quit")
    if filt:
        keys = f"/{filt}_   (esc clears)"
    usage = ""
    if not lim:
        usage = f"{THEME['name']} · api est ${fleet:.2f}"
    elif SHOW_COST:
        usage = f"api est ${fleet:.2f} (the plan is a flat fee; this is what the tokens would cost on the API)"
    out = [("rule", rule(W))]
    kw, groups = W - dw(d) - 1, keys.split(" · ")
    optional = ["$ cost", "+/- zoom", "p wording", "🎨 t theme", "t theme", "c resume", "O in IDE", "o read plan", "w rabbit",
                "👻 h hidden", "h hidden", "🔵 b hide", "b hide", "🔴 r kill", "r kill"]
    while True:
        klines, cur = [], ""
        for grp in groups:                       # wrap between key groups, never inside one
            cand = f"{cur} · {grp}" if cur else grp
            if dw(cand) <= kw or not cur:
                cur = cand
            else:
                klines.append(cur); cur = grp
        klines.append(cur)
        if len(klines) <= 3 or not optional:     # narrow terminal: shed the optional keys (? manual lists them)
            break
        groups.remove(optional.pop(0)) if optional[0] in groups else optional.pop(0)
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
    sep = " │ " if G is not ASCII else " | "
    stale = f" (as of {age_str(best_ts)} ago)" if age > 120 else ""   # numbers come from the last API reply any session saw
    return sep.join(parts) + stale


MANUAL = """
  ⌐■-■  T H E  O P E R A T O R                                          dodge this

  Every Claude Code session on this machine, one row each. Rows sort ringing first.

  ☎  ring 12m    the session waits on you (turn ended, or a permission prompt), and for how long
  red ctx        context past 80%: /compact before the next review panel eats the budget.
                 Crossing it fires a toast, and a desktop notification when `n` is on.
  "quoted" task  a session with no anderson pipeline shows its first prompt as the title
  ▶  work        model thinking, or a tool / subagent running
  ✝  sentinel    the process is gone; the row stays until you blue-pill it
  ⟲  déjà vu     the loop repeated (iteration > 0)

  persona   who is on the job, from feature-research/*/state.md: ARCHITECT plan,
            INTERROGATOR grill (you), ORACLE plan_review, NEO implement,
            AGENT SMITH diff_review, THE ONE shipped, T. ANDERSON: no pipeline yet
  ctx       from the statusline heartbeat (bin/heartbeat.py); falls back to the transcript's
            last usage when no heartbeat is wired
  footer    session 46% · 4h07 left │ week 41% · resets Fri 19:00   (red past 90%: extra-usage
            credits are next). Numbers are the last API reply any session saw: fleet cannot ask
            the API itself, so "(as of 4m ago)" appears when they are older than two minutes.
            session = the rolling 5-hour window (/usage "Current session"), week = the 7-day
            window for all models. Your plan is a flat fee: these percentages ARE the cost.
            Claude Code does not expose the per-model weekly number.
  api$      hidden on subscriptions. `$` (or --cost) shows Claude Code's list-price estimate
            per session: a burn gauge (which session eats most), never your bill.

  ↑↓ / j k  tune           select a session · 1-9 jack straight into row N
  o         read           read the gate artifact right here: plan.md (grill, plan review),
                           plan.md + audit.md (diff review). glow when installed, else less with
                           a light markdown colouring; q comes back to fleet, :n = next file
  O         open in IDE    same files in your IDE: --editor code (saved), else a GUI
                           $VISUAL/$EDITOR, else the IDE that owns the session. ⏎ / 1-9 on a row
                           parked at a human gate does this automatically when an IDE applies
  c         resume         copy `cd <cwd> && claude --resume <sid>` (bring a sentinel back)
  m         sound          on/off (saved): the picked sound plays when a session starts waiting
  s         ring sound     next sound, previewed and saved: phone (the Matrix call) · snare ·
                           hitech · freeze · blip · rift · jump. --ring NAME picks, --rings lists.
                           Your own: drop .wav files in ~/.claude/fleet/sounds/ (picked by name),
                           or ~/.claude/fleet/ring.wav to override everything
  n         notify         desktop notification when a session starts ringing, or crosses
                           80% context (saved). macOS: brew install terminal-notifier for
                           reliable banners; clicking one brings this terminal forward
  ⏎         jack in        tmux: switch to that pane · macOS without tmux: focus the
                           iTerm2 / Terminal.app tab that owns the session, else bring the
                           owning app forward (WebStorm / VS Code / Cursor integrated terminals)
  w         white rabbit   jump to the oldest ringing session
  r         red pill       kill the session's process (asks first); the row is hidden with it
  b         blue pill      hide the row, any row; the process is left alone. On a hidden row: un-hide
  h         hidden         show the hidden rows too (◌, dim), so you can bring one back with b
  ctrl-L    redraw         repaint the whole screen (also automatic every 10 s and on resize)
  /         filter         substring on repo · task ; esc clears
  t         theme          matrix · construct · zion · nebuchadnezzar · agent (saved)
  p         wording        Matrix lingo (zion · jacked in · ringing · sentinel) or plain (saved)
  $         api$           show/hide the per-session API-price estimate column (saved)
  + / -     zoom           Terminal.app: grow/shrink this window's font while fleet runs (saved,
                           restored on quit; --zoom 16 sets it, --no-zoom clears). iTerm2 / IDE: ⌘+
  ?         this           q quits

  prefs: ~/.claude/fleet/prefs.json (theme · plain · calm; --theme/--plain/--calm set them)
  data:  ~/.claude/fleet/  ·  --no-intro  ·  --ascii  ·  --selftest
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


def notify(title, body):
    """Desktop ping when a session starts waiting or crosses the context line. Fire-and-forget.
    macOS: terminal-notifier when installed (reliable, listed in System Settings, click focuses the
    terminal fleet runs in); else osascript, which recent macOS often swallows. Linux: notify-send."""
    try:
        if sys.platform == "darwin":
            if shutil.which("terminal-notifier"):
                cmd = ["terminal-notifier", "-title", "THE OPERATOR", "-subtitle", title, "-message", body,
                       "-group", "anderson-fleet", "-sound", "default"]
                b = _terminal_bundle()
                if b:
                    cmd += ["-activate", b]
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
    """Which sound rings: your ~/.claude/fleet/ring.wav, else the picked sound (RING; `s` cycles,
    --ring NAME), else the bundled phone, else a synthesized ringback written once to the fleet dir."""
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


def notify_hint():
    """What the `n` toast adds when banners are likely to be swallowed."""
    if sys.platform == "darwin" and not shutil.which("terminal-notifier"):
        return "  (macOS often drops osascript banners: brew install terminal-notifier)"
    return ""


def resume_cmd(r):
    sid = r.get("sid") or ""
    if sid.startswith("pid:") or sid.startswith("demo") or len(sid) < 8:
        return None
    cwd = r.get("cwd") or ""
    return (f"cd {shlex_quote(cwd)} && " if cwd else "") + f"claude --resume {sid}"


def shlex_quote(s):
    import shlex
    return shlex.quote(s)


def copy_resume(r):
    """`c`: put `cd <cwd> && claude --resume <sid>` on the clipboard. Works for any row; the point is
    bringing a sentinel back."""
    cmd = resume_cmd(r)
    if not cmd:
        return "no session id for that row."
    for tool in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
        if shutil.which(tool[0]):
            try:
                subprocess.run(tool, input=cmd, text=True, timeout=3)
                return f"copied: {cmd}"
            except Exception:
                break
    return f"resume with: {cmd}"


# ──────────────────────────────────────────────────────── open the gate artifact
EDITOR = None
GUI_EDITORS = {"code", "code-insiders", "cursor", "windsurf", "zed", "subl", "webstorm", "idea", "pycharm",
               "phpstorm", "goland", "rubymine", "clion", "rider", "fleet", "mate", "atom", "nova"}


def gate_files(r):
    """The artifacts a human gate asks you to read, for this row's stage. Existing files only."""
    root, task = r.get("root") or r.get("cwd") or "", r.get("task") or ""
    if not root or not task:
        return []
    d = os.path.join(root, "feature-research", task)
    want = {"grill": ["plan.md"], "plan_review": ["plan.md"], "diff_review": ["plan.md", "audit.md"],
            "implement": ["audit.md"]}.get(r.get("stage") or "", ["plan.md"])
    return [os.path.join(d, f) for f in want if os.path.isfile(os.path.join(d, f))]


def editor_cmd(r, files):
    """argv to open files: --editor / $FLEET_EDITOR / a GUI $VISUAL·$EDITOR, else the IDE owning the
    session (macOS), else the OS default opener. None when nothing applies."""
    for cand in (EDITOR, os.environ.get("FLEET_EDITOR"), os.environ.get("VISUAL"), os.environ.get("EDITOR")):
        if cand and os.path.basename(cand.split()[0]) in GUI_EDITORS and shutil.which(cand.split()[0]):
            return cand.split() + files
    if sys.platform == "darwin":
        app = _owner_app(r.get("pid")) if r.get("pid") else None
        if app and app[0] not in ("Terminal", "iTerm2", "Warp", "Ghostty", "Alacritty", "kitty"):
            return ["open", "-a", app[1]] + files
        return None                              # a plain terminal owns it: nothing sensible to open into
    if shutil.which("xdg-open"):
        return ["xdg-open"] + files[:1]
    return None


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
        return ["glow", "-p"] + files, []
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


def view_gate(r, scr=None):
    """`o`: read plan.md / audit.md right here, in the fleet terminal; the TUI resumes on q."""
    import curses
    files = gate_files(r)
    if not files:
        return "nothing to read: no plan.md / audit.md for that row."
    cmd, tmp = view_cmd(files)
    try:
        if scr is not None:
            curses.endwin()
        subprocess.run(cmd)
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
    return f"read {', '.join(os.path.basename(f) for f in files)}{hint}"


def open_gate(r):
    files = gate_files(r)
    if not files:
        return "nothing to open: no plan.md / audit.md for that row."
    cmd = editor_cmd(r, files)
    if not cmd:
        return "no IDE owns that session: o reads it here, or fleet --editor code"
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"opened {', '.join(os.path.basename(f) for f in files)} in {os.path.basename(cmd[0]) if cmd[0] != 'open' else (cmd[2].rsplit('/', 1)[-1] if cmd[1:2] == ['-a'] else 'default app')}"
    except Exception as e:
        return f"open failed: {e}"


# ───────────────────────────────────────────────────────────────────── zoom
# Font size is the terminal's, not ours. Terminal.app exposes it per window over AppleScript, so
# on macOS fleet can grow its own window while it runs and put it back on exit. iTerm2 and IDE
# terminals have no such API: we print the shortcut instead (⌘+ / ⌘-).
def _own_tty():
    try:
        return os.ttyname(sys.stdout.fileno())
    except Exception:
        return None


def _terminal_font(tty, size=None):
    """Terminal.app only. size None -> read current size; int -> set it. Returns int or None."""
    if sys.platform != "darwin" or os.environ.get("TERM_PROGRAM") != "Apple_Terminal" or not tty:
        return None
    action = f"set font size of w to {int(size)}\n          " if size else ""
    script = f"""tell application "Terminal"
  repeat with w in windows
    repeat with t in tabs of w
      if tty of t is "{tty}" then
          {action}return font size of w
      end if
    end repeat
  end repeat
end tell
return """""
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=4)
        out = r.stdout.strip()
        return int(out) if out.isdigit() else None
    except Exception:
        return None


def run_tui(args):
    import curses
    demo = "--demo" in args
    intro = "--no-intro" not in args
    calm = load_prefs()["calm"]
    tty = _own_tty()
    zoom = {"size": load_prefs()["zoom"], "orig": None}
    if zoom["size"]:
        zoom["orig"] = _terminal_font(tty)
        if zoom["orig"]:
            _terminal_font(tty, zoom["size"])

    def zoom_by(delta):
        cur = _terminal_font(tty)
        if cur is None:
            return ("no font control here: Terminal.app only. iTerm2 / IDE: ⌘+ and ⌘-"
                    if sys.platform == "darwin" else "no font control here: use your terminal's zoom (ctrl+shift+= / ctrl+-)")
        if zoom["orig"] is None:
            zoom["orig"] = cur
        new = max(6, min(72, cur + delta))
        _terminal_font(tty, new); save_prefs(zoom=new); zoom["size"] = new
        return f"font {new}pt (saved; window restored to {zoom['orig']}pt on quit)"

    def app(scr):
        global NOTIFY, SHOW_COST, PLAIN, SOUND, RING, SHOW_HIDDEN
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
                "sentinel": col(T["dead"]) | DIM, "sentinel_sel": DIM | REV,
                "hidden": DIM, "hidden_sel": DIM | REV,
                "burst": col(T["accent"]) | BOLD, "det": 0, "quote": col(T["quote"]) | DIM, "foot": DIM,
                "foot_hot": col("red") | BOLD,
            }

        if intro:
            boot(scr, curses, col)
        rows, sel, filt, filt_mode = [], 0, "", False
        toast, toast_until = "", 0
        confirm = None
        manual = False
        typed = ""
        rung, shipped, burst, hot_seen = set(), set(), {}, set()
        last_scan = 0
        last_full = 0          # a full repaint every FULL_REPAINT_S: a Space swipe or an app switch can leave stale cells
        prev = None            # last painted (size, lines-with-attrs): repaint only on change

        def say(msg, secs=3):
            nonlocal toast, toast_until
            toast, toast_until = msg, time.time() + secs

        while True:
            now = time.time()
            frame = int(now)   # 1 fps animation clock, whatever the input poll rate
            if now - last_scan > REFRESH_S:
                all_rows = discover()
                if demo:
                    all_rows = demo_rows() + all_rows
                new_ring = {r["sid"] for r in all_rows if r["status"] == "ring"}
                for sid in new_ring - rung:
                    r = next(x for x in all_rows if x["sid"] == sid)
                    if last_scan and THEME["eggs"] != "quiet":
                        say(f"Wake up, Neo…  {r['repo']} · {r['task'] or 'session'} needs you.", 5)
                    watched = last_scan and (NOTIFY or SOUND) and looking_at(r)
                    if watched:
                        say(f"{r['repo']} · {r['task'] or 'session'} needs you — you're on it, no ping.", 4)
                    if last_scan and NOTIFY and not watched:
                        notify(f"{r['repo']} · {r['task'] or r.get('title') or 'session'}", r["now"])
                    if last_scan and SOUND and not watched:
                        ring_sound()
                rung = new_ring
                new_hot = hot_rows(all_rows)
                for sid in new_hot - hot_seen:
                    r = next(x for x in all_rows if x["sid"] == sid)
                    if last_scan:
                        say(f"context {int(r['ctx_pct'])}% on {r['repo']} · {r['task'] or r.get('title') or 'session'}: /compact before it eats the budget.", 6)
                        if NOTIFY:
                            notify(f"{r['repo']} · {r['task'] or r.get('title') or 'session'}", f"context {int(r['ctx_pct'])}%: /compact")
                hot_seen = new_hot            # drops below the line (after a /compact) re-arms the alert
                new_ship = {r["sid"] for r in all_rows if r["shipped"]}
                for sid in new_ship - shipped:
                    if last_scan:
                        burst[sid] = now + 1.2
                        if THEME["eggs"] != "quiet":
                            say("He is The One.", 4)
                shipped = new_ship
                rows = [r for r in all_rows if not filt or filt.lower() in (r["repo"] + " " + r["task"]).lower()]
                sel = min(sel, max(0, len(rows) - 1))
                last_scan = now
            burst = {k: v for k, v in burst.items() if v > now}
            if toast and now > toast_until:
                toast = ""
            h, w = scr.getmaxyx()
            if now - last_full > FULL_REPAINT_S:
                prev = None; last_full = now
            A = attrs()
            if manual:
                painted = [(fit(ln, w - 1), A["hdr"] if y == 0 else 0)
                           for y, ln in enumerate(MANUAL.strip("\n").split("\n")[: h - 1])]
            else:
                shown_toast = confirm or toast
                lines = render(rows, w - 1, sel, frame, filt if filt_mode else "", shown_toast, set(burst), now, height=h - 1)
                painted = []
                hot = set()
                span = ctx_span(w - 1)
                top = next((i for i, (k, _) in enumerate(lines) if k == "colhdr"), 2) + 1   # first row's line
                for y, (kind, ln) in enumerate(lines[: h - 1]):
                    a = A.get(kind, 0)
                    if kind == "ring" and THEME.get("pulse") and frame % 2:
                        a = col(THEME["ring"]) | DIM          # breathe, once a second
                    if kind == "quote" and confirm:
                        a = col("red") | BOLD
                    painted.append((ln, a))
                    if span and top <= y < top + len(rows) and kind not in ("burst",):
                        r = rows[y - top]
                        if r["ctx_pct"] is not None and r["ctx_pct"] >= HOT_CTX and r["status"] != "sentinel":
                            hot.add(y)
                hot_key = tuple(sorted(hot))
            if manual:
                hot, hot_key, span = set(), (), None
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
            if confirm:
                if k in (ord("y"), ord("Y")):
                    r = rows[sel]
                    if r["pid"]:
                        try:
                            os.kill(int(r["pid"]), signal.SIGTERM)
                            dismiss(r["sid"]); last_scan = 0
                            say(f"red pill: SIGTERM → pid {r['pid']} · row hidden")
                        except Exception as e:
                            say(f"red pill failed: {e}")
                    else:
                        say("no pid for that session (demo or unknown)")
                else:
                    say("blue sky. nothing happened.")
                confirm = None; continue
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
            if k in (ord("q"), 27):
                return
            if k in (curses.KEY_DOWN, ord("j")):
                sel = min(sel + 1, max(0, len(rows) - 1))
            elif k in (curses.KEY_UP, ord("k")):
                sel = max(sel - 1, 0)
            elif k in (10, 13, curses.KEY_ENTER):
                if rows:
                    say(jack_in(rows[sel]) + gate_auto_open(rows[sel]))
            elif k == ord("o"):
                if rows:
                    say(view_gate(rows[sel], scr), 4); prev = None; last_full = now
            elif k == ord("O"):
                if rows:
                    say(open_gate(rows[sel]))
            elif k == ord("w"):
                ringing = [i for i, r in enumerate(rows) if r["status"] == "ring"]
                if ringing:
                    sel = min(ringing, key=lambda i: rows[i]["last_seen"]); say("follow the white rabbit.")
                else:
                    say("no rabbit. nobody is ringing.")
            elif k == ord("r"):
                if rows:
                    confirm = f"red pill: kill {rows[sel]['repo']} · {rows[sel]['task'] or rows[sel]['sid'][:8]} ?  How far down does the rabbit hole go? [y/N]"
            elif k == ord("b"):
                if rows and rows[sel].get("hidden"):
                    unhide(rows[sel]["sid"]); last_scan = 0
                    say("row back in the list.")
                elif rows:
                    r = rows[sel]
                    dismiss(r["sid"], clean=r["status"] == "sentinel"); last_scan = 0
                    live = "" if r["status"] == "sentinel" else " (the session keeps running)"
                    say(f"blue pill: row hidden{live}. you wake up in your bed and believe whatever you want to.  h shows hidden rows", 5)
            elif k == ord("h"):
                SHOW_HIDDEN = not SHOW_HIDDEN; last_scan = 0
                say(f"hidden rows shown ({G['hid']} dim) · b on one brings it back · h hides them again" if SHOW_HIDDEN else "hidden rows hidden.", 5)
            elif k == ord("t"):
                nxt = THEME_ORDER[(THEME_ORDER.index(THEME["name"]) + 1) % len(THEME_ORDER)]
                set_theme(nxt, calm); save_prefs(theme=nxt); prev = None
                say(f"theme: {nxt} — {THEMES[nxt]['desc']}", 4)
            elif k == ord("p"):
                PLAIN = not PLAIN; save_prefs(plain=PLAIN); prev = None
                say("plain english." if PLAIN else "welcome back to the Matrix.")
            elif ord("1") <= k <= ord("9"):
                i = k - ord("1")
                if i < len(rows):
                    sel = i; say(jack_in(rows[sel]) + gate_auto_open(rows[sel]))
            elif k == ord("c"):
                if rows:
                    say(copy_resume(rows[sel]))
            elif k == ord("m"):
                SOUND = not SOUND; save_prefs(sound=SOUND)
                if SOUND:
                    say(f"sound on: '{RING}' rings when a session waits on you.  s picks another sound", 6)
                    ring_sound()
                else:
                    say("sound off.")
            elif k == ord("s"):
                names = sound_names() or ["phone"]
                RING = names[(names.index(RING) + 1) % len(names)] if RING in names else names[0]
                save_prefs(ring=RING)
                if not SOUND:
                    SOUND = True; save_prefs(sound=True)
                say(f"ring: {RING}  ({names.index(RING) + 1}/{len(names)}) · s again for the next · own .wav: ~/.claude/fleet/sounds/", 6)
                ring_sound()
            elif k == ord("n"):
                NOTIFY = not NOTIFY; save_prefs(notify=NOTIFY)
                if NOTIFY:
                    say("desktop notifications on: a ring pings you wherever you are." + notify_hint(), 6)
                    notify("fleet", "notifications on")          # the test banner: seen it, it works
                else:
                    say("desktop notifications off.")
            elif k == ord("$"):
                SHOW_COST = not SHOW_COST; save_prefs(cost=SHOW_COST); prev = None
                say("api$ shown: Claude Code's list-price estimate, a burn gauge, not your bill." if SHOW_COST else "api$ hidden.")
            elif k in (ord("+"), ord("=")):
                say(zoom_by(+1)); prev = None
            elif k in (ord("-"), ord("_")):
                say(zoom_by(-1)); prev = None
            elif k == ord("/"):
                filt_mode = True; filt = ""
            elif k == ord("?"):
                manual = True
            if 32 <= k < 127:
                typed = (typed + chr(k))[-3:]
                if typed == "neo" and THEME["eggs"] != "quiet":
                    say("I know kung fu.", 4)

    try:
        curses.wrapper(app)
    finally:
        if zoom["orig"]:
            _terminal_font(tty, zoom["orig"])


def boot(scr, curses, col):
    """Digital rain resolving into the sigil, 'Loading anderson…' and one rotating line.
    ~1.8s total; --no-intro skips it. Rain is drawn once per 80ms but the centre block is
    stable, so the eye has somewhere to rest."""
    line = boot_line()
    accent = col(THEME["hdr"])
    t0 = time.time()
    rain_until, hold_until = t0 + 0.7, t0 + 1.8
    seed_chars = "01·10 1 0" if G is not ASCII else "01.10 1 0"
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


FOCUS_ITERM = """tell application "iTerm2"
  repeat with w in windows
    repeat with t in tabs of w
      repeat with s in sessions of t
        if tty of s is "{tty}" then
          select s
          select t
          set index of w to 1
          activate
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
        set selected tab of w to t
        set index of w to 1
        activate
        return "ok"
      end if
    end repeat
  end repeat
end tell
return "miss\""""


def _focus_script(app, tty):
    """AppleScript that brings the tab owning `tty` to the front in iTerm2 or Terminal.app."""
    return (FOCUS_ITERM if app == "iTerm2" else FOCUS_TERMINAL).replace("{tty}", tty)


def _focus_tty(tty):
    """macOS: focus the iTerm2 / Terminal.app tab that owns this tty. True on success."""
    if sys.platform != "darwin" or not tty:
        return False
    for app in ("iTerm2", "Terminal"):
        try:
            up = subprocess.run(["osascript", "-e", f'application "{app}" is running'],
                                capture_output=True, text=True, timeout=3).stdout.strip()
            if up != "true":
                continue
            r = subprocess.run(["osascript", "-e", _focus_script(app, tty)], capture_output=True, text=True, timeout=5)
            if r.stdout.strip() == "ok":
                return True
        except Exception:
            continue
    return False


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


def looking_at(r):
    """True when the session's own terminal is what the human is looking at right now, so a desktop
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
        tty = _tty_of(r["pid"])
        if tty and bid in ("com.apple.Terminal", "com.googlecode.iterm2"):
            return _selected_tty(bid) == tty
        owner = _owner_app(r["pid"])                     # IDE terminals: the IDE itself is frontmost
        return bool(owner) and owner[0].lower() in (name.lower(), bid.lower().rsplit(".", 1)[-1])
    except Exception:
        return False


def _owner_app(pid):
    """macOS: the .app that owns this process (WebStorm, VS Code, Cursor, Warp...), via the ppid chain."""
    try:
        seen = 0
        while pid and int(pid) > 1 and seen < 32:
            r = subprocess.run(["ps", "-o", "ppid=,command=", "-p", str(pid)], capture_output=True, text=True, timeout=3)
            parts = r.stdout.strip().split(None, 1)
            if len(parts) < 2:
                return None
            m = re.search(r"(/[^\0]*?/([^/]+)\.app)/Contents/MacOS/", parts[1])
            if m:
                return m.group(2), m.group(1)
            pid = parts[0]; seen += 1
    except Exception:
        pass
    return None


def gate_auto_open(r):
    """Jacking into a session parked at a human gate also opens what the gate wants read."""
    if r.get("gate") == "human" and gate_files(r):
        return "  ·  " + open_gate(r)
    return ""


def jack_in(r):
    """⏎: bring that session to the front. tmux pane first; else the terminal tab owning the
    session's tty (macOS iTerm2 / Terminal.app via AppleScript); else say what would work."""
    pane = r.get("tmux_pane")
    if pane:
        try:
            sess_name = subprocess.run(["tmux", "display", "-p", "-t", pane, "#S"],
                                       capture_output=True, text=True, timeout=3).stdout.strip()
            if os.environ.get("TMUX"):
                subprocess.run(["tmux", "switch-client", "-t", sess_name], timeout=3)
            subprocess.run(["tmux", "select-window", "-t", pane], timeout=3)
            subprocess.run(["tmux", "select-pane", "-t", pane], timeout=3)
            if not os.environ.get("TMUX"):
                # fleet runs outside tmux: also focus the terminal tab holding that tmux client
                ct = subprocess.run(["tmux", "list-clients", "-t", sess_name, "-F", "#{client_tty}"],
                                    capture_output=True, text=True, timeout=3).stdout.split()
                if not any(_focus_tty(t) for t in ct):
                    return f"pane {r.get('tmux_addr') or pane} selected. attach with: tmux attach -t {sess_name}"
            return "Operator."
        except Exception as e:
            return f"jack in failed: {e}"
    tty = _tty_of(r.get("pid")) if r.get("pid") else None
    if tty and _focus_tty(tty):
        return "Operator."
    if sys.platform == "darwin":
        app = _owner_app(r.get("pid")) if r.get("pid") else None
        if app:
            name, path = app
            try:
                subprocess.run(["open", "-a", path], timeout=5)
                return f"Operator. ({name} integrated terminal: app focused, tab not selectable)"
            except Exception:
                pass
        return "no tmux pane, and no iTerm2/Terminal.app tab owns that session. start it in tmux to jack in."
    return "no tmux pane for that session. start it inside tmux to jack in."


# ─────────────────────────────────────────────────────────────────── main
def selftest():
    random.seed(7)
    words = ["fashion-webapp-2", "ai-shoot-service", "claude-loop", "x", "a-very-long-repository-name-that-goes-on",
             "ar-2270-sku-images-lightbox", "déjà-vu-tâche-éè", "日本語のタスク", "remove-db-triggers", ""]
    stages = list(PERSONA) + [""]
    fails = 0
    for theme in THEME_ORDER:
        set_theme(theme)
        for width in list(range(60, 221, 7)) + [40, 300]:
            rows = []
            for i in range(12):
                st = random.choice(stages)
                gk, persona, ms, mood = PERSONA.get(st, ("none", "T. ANDERSON", "", ""))
                rows.append(dict(sid=f"s{i}", pid=None, cwd="", root="", repo=random.choice(words), task=random.choice(words),
                                 stage=st, persona=persona, pglyph=PGLYPH[gk], mood=mood, model=ms.format(rm="fable") or "fable",
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
    print("alignment selftest:", "FAIL" if fails else "ok", f"({fails} bad lines, {len(THEME_ORDER)} themes)")
    return 1 if fails else 0


def main(argv):
    args = argv[1:]
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
    for a in args:
        if a.startswith("--zoom="):
            prefs["zoom"] = int(a.split("=", 1)[1]) if a.split("=", 1)[1].isdigit() else None
    if "--zoom" in args and args.index("--zoom") + 1 < len(args) and args[args.index("--zoom") + 1].isdigit():
        prefs["zoom"] = int(args[args.index("--zoom") + 1])
    if "--no-zoom" in args:
        prefs["zoom"] = None
    if "--cost" in args:
        prefs["cost"] = True
    if "--no-cost" in args:
        prefs["cost"] = False
    if "--editor" in args and args.index("--editor") + 1 < len(args):
        prefs["editor"] = args[args.index("--editor") + 1]
    for a in args:
        if a.startswith("--editor="):
            prefs["editor"] = a.split("=", 1)[1]
    global EDITOR
    EDITOR = prefs["editor"]
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
        print("  hear one: fleet --play NAME   ·   pick: fleet --ring NAME   ·   in the TUI: s")
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
        save_prefs(theme=theme, plain=prefs["plain"], calm=prefs["calm"], zoom=prefs["zoom"], cost=prefs["cost"], notify=prefs["notify"], editor=prefs["editor"], sound=prefs["sound"], ring=prefs["ring"])
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
        rows = discover()
        if "--demo" in args:
            rows = demo_rows() + rows
        for _, ln in render(rows, width, sel=0, frame=int(time.time()) % 4):
            print(ln)
        return
    run_tui(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
