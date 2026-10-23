#!/usr/bin/env python3
"""Hold the report's word that upstream OpenBMC no longer builds either board to `openbmc/openbmc`, at a revision.

    check_layers.py --rev SHA

At that revision `meta-facebook/` holds no machine layer for the Yosemite V2 or the Yosemite V3.5 baseboard: no
`meta-yosemitev2`, no `meta-greatlakes`, no `meta-fby35`. The last commit before it to touch `meta-yosemitev2`
deletes it, and so does the last to touch `meta-greatlakes`, both committed on 16 May 2025; the last to touch
`meta-fby35` renames it to `greatlakes`, committed in 2022. It exits 0 only when all of that holds.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

API = "https://api.github.com/repos/openbmc/openbmc"
GONE = ("meta-yosemitev2", "meta-greatlakes", "meta-fby35")
# The last commit to touch each layer, as the report states it: its subject, and the day it was committed.
LAST = {
    "meta-yosemitev2": ("meta-facebook: delete yosemitev2", "2025-05-16"),
    "meta-greatlakes": ("meta-facebook: delete greatlakes", "2025-05-16"),
    "meta-fby35": ("fby35: Rename to greatlakes", "2022"),
}


def get(path: str):
    request = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json",
                                                          "User-Agent": "check-layers"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rev", required=True, help="the openbmc/openbmc revision the report names")
    args = ap.parse_args(argv)
    layers = {entry["name"] for entry in get(f"/contents/meta-facebook?ref={args.rev}")}
    checks = {f"meta-facebook/ holds no {name}": name not in layers for name in GONE}
    for name, (subject, day) in LAST.items():
        commits = get(f"/commits?path=meta-facebook/{name}&sha={args.rev}&per_page=1")
        last = commits[0]["commit"] if commits else {}
        checks[f"the last commit to {name} is '{subject}', committed {day}"] = (
            last.get("message", "").split("\n", 1)[0] == subject
            and last.get("committer", {}).get("date", "").startswith(day))
    for what, held in checks.items():
        print(f"{'holds ' if held else 'FAILS '} {what}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
