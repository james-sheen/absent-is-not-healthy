#!/usr/bin/env python3
"""Hold a sentence of the report to the published document it rests on, at the revision the report names.

    check_text.py URL PHRASE [PHRASE ...]

Fetches the document and exits 0 only when every phrase appears in it, any run of whitespace -- a line wrap
included -- read as one space, so a phrase is found however the document happens to be wrapped. A phrase that is
missing is named. The URL names the revision, as a tag or a commit: a sentence is a claim about one version of a
document, never about whatever it says today.
"""
from __future__ import annotations

import sys
import urllib.request


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    url, phrases = args[0], args[1:]
    with urllib.request.urlopen(url, timeout=30) as response:
        text = " ".join(response.read().decode("utf-8").split())
    missing = [p for p in phrases if " ".join(p.split()) not in text]
    for phrase in missing:
        print(f"NOT FOUND in {url}: {phrase!r}", file=sys.stderr)
    print(f"{len(phrases) - len(missing)} of {len(phrases)} phrase(s) found in {url}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
