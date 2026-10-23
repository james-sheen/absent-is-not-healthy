#!/usr/bin/env python3
"""Hold the report's reading of dbus-sensors to its source, at the revision the report names.

    check_consumer.py --rev SHA

Reads `src/Thresholds.cpp` and `src/Thresholds.hpp` at that revision and exits 0 only when what the report
says still holds there: `parseThresholdsFromConfig` reads a threshold's `Direction`, `Severity` and `Value` and
never its `Name`; `less than` is a low threshold; `Severity` 1 is critical; and a low threshold asserts when
the value is at or below it.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request

RAW = "https://raw.githubusercontent.com/openbmc/dbus-sensors/{rev}/src/{name}"


def source(rev: str, name: str) -> str:
    with urllib.request.urlopen(RAW.format(rev=rev, name=name), timeout=30) as response:
        return response.read().decode("utf-8")


def function_body(text: str, name: str) -> str:
    """From the function's definition to the next definition at the start of a line."""
    start = re.search(rf"^\w[\w:<>, ]*\b{name}\(", text, re.MULTILINE)
    if not start:
        return ""
    end = re.search(r"^\w[\w:<>, ]*\b\w+\(", text[start.end():], re.MULTILINE)
    return text[start.start():start.end() + end.start()] if end else text[start.start():]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rev", required=True)
    args = ap.parse_args(argv)
    cpp, hpp = source(args.rev, "Thresholds.cpp"), source(args.rev, "Thresholds.hpp")
    parse = function_body(cpp, "parseThresholdsFromConfig")
    direction = function_body(cpp, "findThresholdDirection")
    checks = {
        "parseThresholdsFromConfig is defined": bool(parse),
        "it reads Direction, Severity and Value": all(f'"{k}"' in parse for k in ("Direction", "Severity", "Value")),
        "it never reads Name": '"Name"' not in parse,
        "less than is a low threshold": bool(re.search(r'"less than"\)\s*\{?\s*return Direction::LOW', direction)),
        "Severity 1 is critical": "{Level::CRITICAL, 1," in hpp,
        "a low threshold asserts at or below its value": "value <= threshold.value" in cpp,
    }
    for what, held in checks.items():
        print(f"{'holds ' if held else 'FAILS '} {what}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
