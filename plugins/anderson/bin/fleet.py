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

Data, richest first, each optional (the view degrades, never breaks):
  ~/.claude/fleet/<sid>.status.json   heartbeat from bin/heartbeat.py (statusline): $, ctx, model
  ~/.claude/fleet/<sid>.event.json    hooks/fleet_event.py: waiting-on-you vs working
  ~/.claude/projects/<cwd>/<sid>.jsonl transcript tail: last tool, last words, ctx tokens
  <repo>/feature-research/*/state.md  anderson stage/verdicts/iteration -> persona
  ps + lsof + tmux                    sessions with no hooks at all, and the pane to jack into

Keys: ↑↓/jk tune · ⏎ jack in (tmux) · w white rabbit (oldest ring) · r red pill (kill)
      b blue pill (dismiss sentinel) · / filter · t theme · p wording · ? manual · q
Prefs (theme, wording, motion) persist in ~/.claude/fleet/prefs.json.
"""
import glob, json, os, random, re, shutil, signal, subprocess, sys, time, unicodedata

FLEET_DIR = os.path.expanduser(os.environ.get("ANDERSON_FLEET_DIR", "~/.claude/fleet"))
PROJECTS = os.path.expanduser("~/.claude/projects")
HERE = os.path.dirname(os.path.abspath(__file__))
STALE_S = 24 * 3600          # forget sessions with no sign of life for a day
CTX_WINDOW = 200_000         # fallback when the heartbeat has no context_window_size
REFRESH_S = 2.0

# ──────────────────────────────────────────────────────────────────────── glyphs
UNI = dict(eyes="⌐■-■", cur="▸", ring="☎", dead="✝", loop="⟲", run="▶", ship="★",
           bar="▓", trk="░", rule="─", ell="…", det="▍",
           rain=("0·1 1", "1 0·1", " 1·10", "1·0 1"), raincol="01·10")
ASCII = dict(eyes="[-_-]", cur=">", ring="!", dead="x", loop="~", run=">", ship="*",
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
          ("task", "stage", "iteration", "max_iterations", "plan_verdict", "diff_verdict", "review_model", "branch")}
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


def discover(include_ps=True):
    """Merge heartbeat, hook events, ps discovery and transcripts into session dicts."""
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
    panes = _tmux_panes() if ps else {}
    known_pids = {s.get("pid") for s in sess.values()}
    claimed = {s.get("transcript_path") for s in sess.values()}
    orphans = [s for s in sess.values() if not s.get("pid") and s.get("cwd")]
    for pid, _, cmd in ps:
        if pid == os.getpid() or not _is_claude(cmd) or pid in known_pids:
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
        if s["sid"] in dismissed:
            continue
        rows.append(enrich(s, now))
    rows = [r for r in rows if r is not None]
    rows.sort(key=lambda r: ({"ring": 0, "work": 1, "sentinel": 2}.get(r["status"], 1), r["repo"], r["task"]))
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
        "dejavu": bool(it and it.isdigit() and int(it) > 0),
        "status": status, "now": now_txt, "text": tr.get("text") or "",
        "cost": s.get("cost_usd"), "ctx_pct": ctx_pct,
        "lines": (s.get("lines_added"), s.get("lines_removed")),
        "start": start, "last_seen": last_seen,
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
            "cost": bool(d.get("cost")), "notify": bool(d.get("notify"))}


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


def render(rows, width, sel=0, frame=0, filt="", toast="", burst=(), t=None):
    """Pure: -> list of (kind, line). Every line is exactly `width` cells (see --selftest)."""
    t = time.time() if t is None else t
    W = max(40, width)
    cols = layout(W)
    lines = []
    n_ring = sum(r["status"] == "ring" for r in rows)
    n_dead = sum(r["status"] == "sentinel" for r in rows)
    n_live = len(rows) - n_dead
    left = f"{G['eyes']}  T H E  O P E R A T O R"
    right = f"{words('fleet')} · {n_live} {words('live')} · {n_ring} {words('ring')} · {n_dead} {words('deads' if n_dead != 1 else 'dead')}{header_tail(frame)}"
    lines.append(("hdr", fit(fit(left, max(0, W - dw(right) - 1)) + " " + right, W)))
    lines.append(("rule", rule(W)))
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
            kind = r["status"] + ("_sel" if i == sel else "")
        lines.append((kind, fit(f"{num}{cur} {body}", W)))
    lines.append(("rule", rule(W)))
    d = G["det"]
    if rows and 0 <= sel < len(rows):
        r = rows[sel]
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
    else:
        l1 = f"{d} " + ("filter: " + filt if filt else "")
        l2 = f"{d} {toast}" if toast else f"{d} "
        l3 = f"{d} "
    lines += [("det", fit(l1, W)), ("det", fit(l2, W)), ("quote", fit(l3, W))]
    lines.append(("rule", rule(W)))
    fleet = sum(r["cost"] or 0 for r in rows)
    lim = usage_limits()
    keys = f"↑↓ tune  1-9/⏎ jack in  w rabbit  r red pill  b blue pill  c resume  n notify  / filter  t theme  p wording  ? manual  q" \
        if G is not ASCII else "jk tune  1-9/enter jack in  w rabbit  r red pill  b blue pill  c resume  n notify  / filter  t theme  p wording  ? manual  q"
    if filt:
        keys = f"/{filt}_   (esc clears)"
    if lim:
        tot = f"{THEME['name']} · {lim}" + (f" · api est ${fleet:.2f}" if SHOW_COST else "")
    else:
        tot = f"{THEME['name']} · api est ${fleet:.2f}"
    lines.append(("foot", fit(fit(keys, max(0, W - dw(tot) - 1)) + " " + tot, W)))
    return lines


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


def usage_limits():
    """Subscription windows from the freshest heartbeat that carries them (account-wide, so any
    session's copy is the truth), in words:
      'session 46% · 4h07 left │ week 41% · resets Fri 19:00'
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
    parts = []
    for key, label in (("five_hour", "session"), ("seven_day", "week"), ("spend_limit", "spend")):
        w = best.get(key) or {}
        if w.get("pct") is None:
            continue
        r = _reset_str(w.get("resets_at"))
        parts.append(f"{label} {int(w['pct'])}%" + (f" · {r}" if r else ""))
    sep = " │ " if G is not ASCII else " | "
    return sep.join(parts)


MANUAL = """
  ⌐■-■  T H E  O P E R A T O R                                          dodge this

  Every Claude Code session on this machine, one row each. Rows sort ringing first.

  ☎  ring 12m    the session waits on you (turn ended, or a permission prompt), and for how long
  red ctx        context past 80%: /compact before the next review panel eats the budget
  "quoted" task  a session with no anderson pipeline shows its first prompt as the title
  ▶  work        model thinking, or a tool / subagent running
  ✝  sentinel    the process is gone; the row stays until you blue-pill it
  ⟲  déjà vu     the loop repeated (iteration > 0)

  persona   who is on the job, from feature-research/*/state.md: ARCHITECT plan,
            INTERROGATOR grill (you), ORACLE plan_review, NEO implement,
            AGENT SMITH diff_review, THE ONE shipped, T. ANDERSON: no pipeline yet
  ctx       from the statusline heartbeat (bin/heartbeat.py); falls back to the transcript's
            last usage when no heartbeat is wired
  footer    session 46% · 4h07 left │ week 41% · resets Fri 19:00
            session = the rolling 5-hour window (/usage "Current session"), week = the 7-day
            window for all models. Your plan is a flat fee: these percentages ARE the cost.
            Claude Code does not expose the per-model weekly number.
  api$      hidden on subscriptions. `$` (or --cost) shows Claude Code's list-price estimate
            per session: a burn gauge (which session eats most), never your bill.

  ↑↓ / j k  tune           select a session · 1-9 jack straight into row N
  c         resume         copy `cd <cwd> && claude --resume <sid>` (bring a sentinel back)
  n         notify         desktop notification when a session starts ringing (saved)
  ⏎         jack in        tmux: switch to that pane · macOS without tmux: focus the
                           iTerm2 / Terminal.app tab that owns the session, else bring the
                           owning app forward (WebStorm / VS Code / Cursor integrated terminals)
  w         white rabbit   jump to the oldest ringing session
  r         red pill       kill the session's process (asks first)
  b         blue pill      dismiss a sentinel row
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


def notify(title, body):
    """Desktop ping when a session starts waiting. macOS: Notification Center. Linux: notify-send.
    Fire-and-forget; never blocks the UI."""
    try:
        if sys.platform == "darwin":
            esc = lambda t: t.replace("\\", "\\\\").replace('"', '\\"')
            subprocess.Popen(["osascript", "-e", f'display notification "{esc(body)}" with title "THE OPERATOR" subtitle "{esc(title)}"'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which("notify-send"):
            subprocess.Popen(["notify-send", f"THE OPERATOR · {title}", body], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


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
    dismissed_path = os.path.join(FLEET_DIR, "dismissed")
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
        global NOTIFY, SHOW_COST, PLAIN
        curses.curs_set(0)
        scr.timeout(100)
        col = _colors(curses)
        BOLD, DIM, REV = curses.A_BOLD, curses.A_DIM, curses.A_REVERSE

        def attrs():
            T = THEME
            return {
                "hdr": col(T["hdr"]) | BOLD, "rule": col(T["accent"]) | DIM, "colhdr": DIM, "empty": col(T["hdr"]),
                "work": 0, "work_sel": REV,
                "ring": col(T["ring"]) | BOLD, "ring_sel": col(T["ring"]) | BOLD | REV,
                "sentinel": col(T["dead"]) | DIM, "sentinel_sel": DIM | REV,
                "burst": col(T["accent"]) | BOLD, "det": 0, "quote": col(T["quote"]) | DIM, "foot": DIM,
            }

        if intro:
            boot(scr, curses, col)
        rows, sel, filt, filt_mode = [], 0, "", False
        toast, toast_until = "", 0
        confirm = None
        manual = False
        typed = ""
        rung, shipped, burst = set(), set(), {}
        last_scan = 0
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
                    if last_scan and NOTIFY:
                        notify(f"{r['repo']} · {r['task'] or r.get('title') or 'session'}", r["now"])
                rung = new_ring
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
            A = attrs()
            if manual:
                painted = [(fit(ln, w - 1), A["hdr"] if y == 0 else 0)
                           for y, ln in enumerate(MANUAL.strip("\n").split("\n")[: h - 1])]
            else:
                shown_toast = confirm or toast
                lines = render(rows, w - 1, sel, frame, filt if filt_mode else "", shown_toast, set(burst), now)
                painted = []
                hot = set()
                span = ctx_span(w - 1)
                for y, (kind, ln) in enumerate(lines[: h - 1]):
                    a = A.get(kind, 0)
                    if kind == "ring" and THEME.get("pulse") and frame % 2:
                        a = col(THEME["ring"]) | DIM          # breathe, once a second
                    if kind == "quote" and confirm:
                        a = col("red") | BOLD
                    painted.append((ln, a))
                    if span and 3 <= y < 3 + len(rows) and kind not in ("burst",):
                        r = rows[y - 3]
                        if r["ctx_pct"] is not None and r["ctx_pct"] >= HOT_CTX and r["status"] != "sentinel":
                            hot.add(y)
                hot_key = tuple(sorted(hot))
            if manual:
                hot, hot_key, span = set(), (), None
            key = ((h, w), painted, hot_key)
            if key != prev:                                 # repaint only the lines that changed
                full = prev is None or prev[0] != (h, w)
                if full:
                    scr.erase()
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
            if k == curses.KEY_RESIZE:
                prev = None; continue
            if manual:
                manual = False; continue
            if confirm:
                if k in (ord("y"), ord("Y")):
                    r = rows[sel]
                    if r["pid"]:
                        try:
                            os.kill(int(r["pid"]), signal.SIGTERM); say(f"red pill: SIGTERM → pid {r['pid']}")
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
                    say(jack_in(rows[sel]))
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
                if rows and rows[sel]["status"] == "sentinel":
                    sid = rows[sel]["sid"]
                    try:
                        os.makedirs(FLEET_DIR, exist_ok=True)
                        with open(dismissed_path, "a") as f:
                            f.write(sid + "\n")
                        for p in glob.glob(os.path.join(FLEET_DIR, sid + ".*.json")):
                            os.remove(p)
                    except Exception:
                        pass
                    say("blue pill. you wake up in your bed and believe whatever you want to."); last_scan = 0
                elif rows:
                    say("the blue pill is for sentinels only.")
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
                    sel = i; say(jack_in(rows[sel]))
            elif k == ord("c"):
                if rows:
                    say(copy_resume(rows[sel]))
            elif k == ord("n"):
                NOTIFY = not NOTIFY; save_prefs(notify=NOTIFY)
                say("desktop notifications on: a ring pings you wherever you are." if NOTIFY else "desktop notifications off.")
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
    return f"/dev/{t}" if t and t not in ("??", "-", "?") else None


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
                          render([], width), render(rows, width, filt="abc")):
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
    if "--notify" in args:
        prefs["notify"] = True
    if "--no-notify" in args:
        prefs["notify"] = False
    global SHOW_COST, NOTIFY
    SHOW_COST = prefs["cost"]; NOTIFY = prefs["notify"]
    PLAIN = prefs["plain"]
    if theme in THEMES and "--selftest" not in args and "--once" not in args:
        save_prefs(theme=theme, plain=prefs["plain"], calm=prefs["calm"], zoom=prefs["zoom"], cost=prefs["cost"], notify=prefs["notify"])
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
    main(sys.argv)
