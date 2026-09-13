#!/usr/bin/env python3
"""Count installs by fetching a one-byte release asset, once per version, per machine.

A marketplace install is a shallow clone, which GitHub's traffic API counts, but
an *update* is a fetch, which it does not, and the install step itself never
touches the network at all. So the plugin says hello once instead: it downloads
the `ping` asset attached to its own release, and GitHub's public
`download_count` on that asset is the counter. No endpoint to host, no account,
no third party, and no payload -- the request carries no identifier, no path, no
machine or user information. GitHub sees an IP it already saw at clone time.

Opt out with ANDERSON_NO_TELEMETRY=1 (or the cross-tool DO_NOT_TRACK=1).
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MARK = pathlib.Path.home() / ".claude" / "anderson" / "counted"


def version(root=ROOT):
    return json.loads((root / ".claude-plugin" / "plugin.json").read_text())["version"]


def opted_out(env=None):
    env = os.environ if env is None else env
    return bool(env.get("ANDERSON_NO_TELEMETRY") or env.get("DO_NOT_TRACK"))


def claim(ver, mark=MARK):
    """True the first time this version is seen on this machine, False after.

    The marker is written before the request goes out, so a hung or failed ping
    undercounts rather than firing again on every session.
    """
    seen = mark.read_text().split() if mark.exists() else []
    if ver in seen:
        return False
    mark.parent.mkdir(parents=True, exist_ok=True)
    with mark.open("a") as f:
        f.write(ver + "\n")
    return True


def main():
    try:
        if opted_out():
            return
        ver = version()
        if not claim(ver):
            return
        curl = shutil.which("curl")
        if not curl:
            return
        url = f"https://github.com/amj-lang/anderson/releases/download/v{ver}/ping"
        # Detached: a slow network must never hold up the session.
        subprocess.Popen(
            [curl, "-sL", "-m", "5", "-o", os.devnull, url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
        )
    except Exception:
        pass  # a counter is never worth breaking a session over


if __name__ == "__main__":
    main()
    sys.exit(0)
