#!/usr/bin/env python3
"""Hold section 2 to what the released tool does with an incomplete walk, against a gone sensor.

    check_walk.py --tool 'bmc-sensor-audit==VERSION' [--pin 'NAME==VERSION' ...] [--expect KEY=VALUE ...]

That version is installed from PyPI into a virtualenv of its own (the cache `measure_corpus.py` keeps), and the
mock BMC that ships in its wheel serves one board three ways, each walked by `capture` and judged by `coverage`
against a declaration of the board's two sensors: whole; with one sensor gone; and whole, but with its sensor
collection answering HTTP 500 -- the failure a naive reader renders as a board with every sensor missing. Each way
reports whether the walk completed, whether absence findings were withheld, how many declared sensors were judged
absent, and the exit code.

The result prints as JSON. With `--expect KEY=VALUE` it exits 0 only when every expectation holds -- the form the
report's claims ledger runs.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

from measure_corpus import venv_python

# Run inside the virtualenv: the mock is the released tool's own, and so is every judgment.
WAYS = r'''
import json, os, subprocess, sys, tempfile
from pathlib import Path
from bmc_sensor_audit.testing.mock_redfish import MockBMC, MockSensor, serve

tool = str(Path(sys.executable).parent / "bmc-sensor-audit")
board = {"Name": "example board", "Probe": "TRUE", "Type": "Board", "Exposes": [
    {"Name": "Inlet_Temp", "Type": "TMP75", "Bus": 1, "Address": "0x48"},
    {"Name": "Fan_CPU_1", "Type": "AspeedFan", "Index": 0}]}
both = [MockSensor(name="Inlet_Temp", reading=22.5), MockSensor(name="Fan_CPU_1", reading=4800.0)]
ways = {"whole": MockBMC(sensors=both),
        "one_gone": MockBMC(sensors=both[:1]),
        "collection_fails": MockBMC(sensors=both, fail={"/redfish/v1/Chassis/1/Sensors": 500})}
out = {}
with tempfile.TemporaryDirectory() as tmp:
    config = Path(tmp) / "board.json"
    config.write_text(json.dumps(board))
    for name, bmc in ways.items():
        walk = Path(tmp) / f"{name}.json"
        with serve(bmc) as url:
            subprocess.run([tool, "capture", "--target", url, "--out", str(walk)], capture_output=True, text=True)
        done = subprocess.run([tool, "coverage", "--config", str(config), "--walk", str(walk), "--json"],
                              capture_output=True, text=True)
        report = json.loads(done.stdout)
        out[name] = {"exit": done.returncode, "walk_complete": report["walk_complete"],
                     "withheld": report["absence_findings_withheld"], "declared": report["counts"]["declared"],
                     "absent": report["counts"]["declared_absent"]}
print(json.dumps(out))
'''


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tool", required=True, metavar="'bmc-sensor-audit==VERSION'")
    ap.add_argument("--expect", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--pin", action="append", default=[], metavar="'NAME==VERSION'",
                    help="pin a further package beside the released tool, e.g. the library it shares")
    args = ap.parse_args(argv)
    done = subprocess.run([str(venv_python(args.tool, *args.pin)), "-c", WAYS], capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f"the walks could not be run:\n{done.stderr}")
    ways = json.loads(done.stdout)
    result = {"tool": args.tool, **{f"{way}_{key}": value for way, found in ways.items() for key, value in found.items()}}
    print(json.dumps(result, indent=1, sort_keys=True))
    wrong = []
    for pair in args.expect:
        key, _, want = pair.partition("=")
        if str(result.get(key)) != want:
            wrong.append(f"{key} {result.get(key)}, expected {want}")
    for line in wrong:
        print(f"DIFFERS: {line}", file=sys.stderr)
    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main())
