#!/usr/bin/env python3
"""Hold section 4 to its two firmware recordings, the released tool that reads them, and the sources that explain them.

    check_firmware.py --tool 'bmc-sensor-audit==VERSION' --bmcweb SHA --qemu TAG [--pin 'NAME==VERSION' ...]
                      [--expect KEY=VALUE ...]

The audit tool's repository is cloned at the tag of the version named, so the recordings and the board's
configurations are the ones that release carries, and that version is installed from PyPI into a virtualenv of
its own -- the one `measure_corpus.py --reader` uses. Then:

- `coverage` runs on the bletchley capture against the board's three vendored configurations: its counts, its exit
  code, how many of its matches were not by an exact name, and the declared-and-absent sensors grouped by the type
  that declares them; with the capture's own record of what it walked;
- the witherspoon documents are read as served: the members of the modern `Sensors` collection, and what the older
  `Thermal` and `Power` documents carry;
- `bmcweb`'s build options are read at the revision named: the default of the option that keeps the older
  documents and what its description promises, and whether their handlers are still in the tree;
- QEMU's bletchley board and AST2600 models are read at the tag named: the device types the board instantiates on
  its I2C buses, and whether the SoC attaches any device to its fan controller.

The result prints as JSON. With `--expect KEY=VALUE` it exits 0 only when every expectation holds -- the form the
report's claims ledger runs; a list compares as its items joined by commas.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from measure_corpus import reader_python

TOOL_REPO = "https://github.com/james-sheen/bmc-sensor-audit"
BMCWEB = "https://raw.githubusercontent.com/openbmc/bmcweb/{rev}/{path}"
QEMU = "https://raw.githubusercontent.com/qemu/qemu/{tag}/{path}"
FIXTURES = Path("tests") / "fixtures"


def fetch(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def coverage(spec: str, clone: Path, pins: tuple = ()) -> dict:
    tool = reader_python(spec, *pins).parent / "bmc-sensor-audit"
    fixtures = clone / FIXTURES
    done = subprocess.run([str(tool), "coverage", "--config", "upstream/meta/bletchley",
                           "--walk", "walk_qemu_bletchley.json", "--json"],
                          cwd=fixtures, capture_output=True, text=True)
    report = json.loads(done.stdout)
    absent = Counter(re.search(r"declared by (\S+)", f["detail"]).group(1)
                     for f in report["findings"] if f["kind"] == "declared_absent")
    walk = json.loads((fixtures / "walk_qemu_bletchley.json").read_text(encoding="utf-8"))
    return {
        "exit_code": done.returncode, "walk_complete": report["walk_complete"],
        "config_files": len(list((fixtures / "upstream" / "meta" / "bletchley").glob("*.json"))),
        "absence_findings_withheld": report["absence_findings_withheld"],
        **{k: report["counts"][k] for k in ("declared", "matched", "reading", "declared_absent", "undeclared_present",
                                              "not_a_sensor")},
        "matched_inexactly": sum(f["kind"] == "matched_inexactly" for f in report["findings"]),
        "absent_by_type": sorted(f"{t}={n}" for t, n in absent.items()),
        "capture_sensors": len(walk["sensors"]), "capture_chassis": len(walk["chassis"]),
        "capture_shapes": sorted(walk["shapes_seen"]),
        "capture_recorded": (re.search(r"Recorded (\d{4}-\d{2}-\d{2})", walk["_provenance"]) or [None, None])[1],
        "capture_image": (re.search(r"image (\S+?\.mtd)", walk["_provenance"]) or [None, None])[1],
        "capture_emulator": (re.search(r"qemu-system-arm ([\d.]+)", walk["_provenance"]) or [None, None])[1],
        "capture_fru_written": "FRU" in walk["_provenance"] and "eeprom@56" in walk["_provenance"],
        "capture_from_openbmc_ci": "jenkins.openbmc.org" in walk["_provenance"],
    }


def witherspoon(clone: Path) -> dict:
    served = json.loads((clone / FIXTURES / "redfish_witherspoon_2_9_0.json").read_text(encoding="utf-8"))
    docs = served["documents"]
    one = lambda suffix: next(v for k, v in docs.items() if k.endswith(suffix))
    thermal, power = one("/Thermal"), one("/Power")
    temperatures, fans = thermal.get("Temperatures", []), thermal.get("Fans", [])
    bounded = lambda entry: any(v is not None for k, v in entry.items() if k.startswith(("Upper", "Lower")))
    return {
        "witherspoon_release": (re.search(r"OpenBMC release ([\d.]+)", served["_provenance"]) or [None, None])[1],
        "witherspoon_published": (re.search(r"published (\d{4})", served["_provenance"]) or [None, None])[1],
        "witherspoon_sensors_members": len(one("/Sensors")["Members"]),
        "witherspoon_temperatures": len(temperatures), "witherspoon_fans": len(fans),
        "witherspoon_temperatures_reading_and_bounded": sum(e.get("ReadingCelsius") is not None and bounded(e)
                                                            for e in temperatures),
        "witherspoon_fans_reading": sum(e.get("Reading") is not None for e in fans),
        "witherspoon_power_carries": sorted(k for k, v in power.items() if isinstance(v, list) and v),
        "witherspoon_power_reading": any(e.get("PowerConsumedWatts") is not None for e in power.get("PowerControl", [])),
    }


def bmcweb(rev: str) -> dict:
    options = fetch(BMCWEB.format(rev=rev, path="meson.options")) or ""
    block = re.search(r"'redfish-allow-deprecated-power-thermal',(.*?)\)", options, re.S)
    text = block.group(1) if block else ""
    present = [fetch(BMCWEB.format(rev=rev, path=f"redfish-core/lib/{n}.hpp")) is not None for n in ("thermal", "power")]
    return {
        "bmcweb_deprecated_default": (re.search(r"value:\s*'(\w+)'", text) or [None, None])[1],
        "bmcweb_deprecated_removal_promised": " ".join(text.split()).count("will be removed June 2026") == 1,
        "bmcweb_deprecated_handlers_present": all(present),
    }


def qemu(tag: str) -> dict:
    board = fetch(QEMU.format(tag=tag, path="hw/arm/aspeed_ast2600_bletchley.c")) or ""
    defined = dict(re.findall(r'#define\s+(TYPE_\w+)\s+"([^"]+)"', board))
    created = {defined.get(t, t.removeprefix("TYPE_").lower()).strip('"')
               for t in re.findall(r"i2c_slave_create_simple\([^,]+,\s*([^,]+),", board)}
    created |= {"at24c-eeprom"} if "at24c_eeprom_init(" in board else set()
    soc = fetch(QEMU.format(tag=tag, path="hw/arm/aspeed_ast2600.c")) or ""
    children = re.findall(r"object_initialize_child\([^;]*?\"([^\"]+)\"", soc, re.S)
    return {
        "qemu_bletchley_i2c_types": sorted(created),
        "qemu_ast2600_fan_controller_device": any("pwm" in c.lower() or "tach" in c.lower() for c in children),
        "qemu_ast2600_fan_controller_mapped": "ASPEED_DEV_PWM" in soc,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tool", required=True, metavar="'bmc-sensor-audit==VERSION'")
    ap.add_argument("--bmcweb", required=True, metavar="SHA")
    ap.add_argument("--qemu", required=True, metavar="TAG")
    ap.add_argument("--expect", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--pin", action="append", default=[], metavar="'NAME==VERSION'",
                    help="pin a further package beside the released tool, e.g. the library it shares")
    args = ap.parse_args(argv)
    version = args.tool.partition("==")[2]
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "tool"
        subprocess.run(["git", "-c", "advice.detachedHead=false", "clone", "-q", "--depth", "1", "--branch",
                        f"v{version}", TOOL_REPO, str(clone)], check=True)
        result = {"tool": args.tool, **coverage(args.tool, clone, tuple(args.pin)), **witherspoon(clone)}
    result |= {"bmcweb": args.bmcweb, **bmcweb(args.bmcweb), "qemu": args.qemu, **qemu(args.qemu)}
    print(json.dumps(result, indent=1, sort_keys=True))
    wrong = []
    for pair in args.expect:
        key, _, want = pair.partition("=")
        got = result.get(key)
        got = ",".join(map(str, got)) if isinstance(got, list) else str(got)
        if got != want:
            wrong.append(f"{key} {got}, expected {want}")
    for line in wrong:
        print(f"DIFFERS: {line}", file=sys.stderr)
    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main())
