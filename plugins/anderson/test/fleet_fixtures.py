"""Four fake session rows for the fleet tests: two ringing, one working, one dead. Takes the loaded
fleet module so the glyphs follow --ascii."""
import time


def demo_rows(fleet):
    G, PGLYPH, PERSONA = fleet.G, fleet.PGLYPH, fleet.PERSONA
    now = time.time()
    base = dict(pid=None, cwd="", root="", title="", plan_verdict="ship", diff_verdict="pending", lines=(212, 48),
                tmux_pane=None, tmux_addr=None, shipped=False, hb_ts=now, last_seen=now, sid="demo",
                branch=None, gate="", ctx_tokens=None, agents=(0, 0, ""), idle=False, transcript_path=None,
                since=now - 60, start_cwd=None, hidden=False)
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
