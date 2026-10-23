#!/usr/bin/env python3
"""Measure entity-manager's configuration corpus at one revision, and hold it to what the report says.

    measure_corpus.py --rev SHA [--checkout DIR] [--reader 'bmc-sensor-audit==VERSION']
                      [--census 'bmc-sensor-audit==VERSION'] [--pin 'NAME==VERSION' ...]
                      [--expect-files N] [--expect-thresholds N] [--expect-direction 'greater than=N' ...]
                      [--expect-contradiction PATH:LABEL=VALUE ...] [--expect KEY=VALUE ...]

Every `.json` file under `configurations/` is read (a file a strict reader refuses is read again with its
C-style block comments stripped, and counted as such), and so is the table of template strings in
`CONFIG_FORMAT.md`. Every `Thresholds` entry anywhere is counted, with its `Direction` and its `Name`'s
spelling, and a threshold whose `Name` says `upper` or `higher` while its `Direction` is `less than`, or
`lower` while it is `greater than`, is listed; every `Exposes` entry that declares its rails in a `Labels`
array is counted, with the rails no threshold names.

With `--reader`, the same checkout is also read by that released version of the audit tool, installed from
PyPI into a virtualenv of its own: what it declares, which of those it classifies as not a sensor or does not
recognise, and which names are runtime templates. Those counts are the released reader's, not this script's.

With `--census`, that released version's own `census --json` runs over the checkout's `configurations/`, and its
result joins this one flattened, under `census.`: `census.files.found`, `census.revision.committed`,
`census.thresholds.by_direction.less than`, and `census.contradictions` in this script's `PATH:LABEL=VALUE` form.
From 0.3.19 the tool counts the corpus itself, so this is the command whose counts are the tool's, not the script's.
**The report's corpus counts are the census's** (switched 2026-10-17): this script's own walk and
`--reader` remain as a second count to compare with, and for what the census does not read -- the format guide, the
schema and the code (`template_strings_documented`, `substitutes_any_property`, `example_threshold_names`, the
`threshold_schema_*` keys).

The result prints as JSON. With any `--expect*`, it exits 0 only when every expectation holds -- the form the
report's claims ledger runs. `--expect KEY=VALUE` compares any key of the result; a list compares as its
items joined by commas.

Without `--checkout`, it fetches the one revision from upstream into a temporary directory: a count is a claim
about a revision, so it is measured at the one the report names, never at whatever a local checkout holds.

`committed` is the revision's commit date, the day its tree was committed -- not the author date of its last
change, which can be weeks earlier: `495e0a4` was written on 2 October 2026 and committed on the 15th, and its
tree holds every change committed in between.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

UPSTREAM = "https://github.com/openbmc/entity-manager"

# Run inside the reader's virtualenv, with the checkout as its argument: the released tool's own reading.
READER_PASS = r'''
import json, re, sys
from collections import Counter
from pathlib import Path
from bmc_sensor_audit.inventory.entity_manager import load_declaration
from bmc_sensor_audit.inventory.sensor_types import NOT_A_SENSOR, UNRECOGNISED, classify

d = load_declaration([Path(sys.argv[1]) / "configurations"])
kinds = Counter(classify(s.type) for s in d.sensors)
types = {k: {s.type for s in d.sensors if classify(s.type) == k} for k in (NOT_A_SENSOR, UNRECOGNISED)}
by_type = lambda kind: [f"{t}={n}" for t, n in sorted(Counter(s.type for s in d.sensors if classify(s.type) == kind)
                                                    .items(), key=lambda tn: (-tn[1], str(tn[0])))]
print(json.dumps({
    "declarations": len(d.sensors), "unreadable": len(d.unreadable), "disabled": len(d.disabled),
    "not_a_sensor": kinds[NOT_A_SENSOR], "not_a_sensor_types": len(types[NOT_A_SENSOR]),
    "not_a_sensor_top10": by_type(NOT_A_SENSOR)[:10],
    "unrecognised": kinds[UNRECOGNISED], "unrecognised_types": len(types[UNRECOGNISED]),
    "unrecognised_by_type": by_type(UNRECOGNISED),
    "templated": len(d.templated),
    "template_strings_used": sorted({m.lower() for s in d.templated for m in re.findall(r"\$[A-Za-z]+", s.name)}),
}))
'''


def fetch(rev: str, into: Path) -> Path:
    for args in (["init", "-q"], ["remote", "add", "origin", UPSTREAM],
                 ["fetch", "-q", "--depth", "1", "origin", rev], ["checkout", "-q", "FETCH_HEAD"]):
        subprocess.run(["git", "-C", str(into), *args], check=True)
    return into


def measure(checkout: Path) -> dict:
    files = sorted((checkout / "configurations").rglob("*.json"))
    stripped, arrays, thresholds, directions, spellings, contradictions = 0, 0, 0, Counter(), Counter(), []
    labelled, max_labels, rails, unbounded = 0, 0, 0, 0
    board, details = None, []

    def walk(node, path):
        nonlocal thresholds, labelled, max_labels, rails, unbounded, board
        if isinstance(node, dict):
            if "Exposes" in node:
                board = node.get("Name")
            for t in node.get("Thresholds") or []:
                if not isinstance(t, dict):
                    continue
                thresholds += 1
                direction, name = t.get("Direction"), str(t.get("Name", "")).lower()
                directions[direction] += 1
                spellings[t.get("Name")] += 1
                says_upper = "upper" in name or "higher" in name
                if (says_upper and direction == "less than") or ("lower" in name and direction == "greater than"):
                    contradictions.append(f"{path}:{t.get('Label')}={t.get('Value')}")
                    details.append(f"{path}:{board}:{node.get('Name')}:{t.get('Label')}:Severity {t.get('Severity')}")
            labels = node.get("Labels")
            if isinstance(labels, list) and labels:
                named = {t.get("Label") for t in node.get("Thresholds") or [] if isinstance(t, dict)}
                labelled, max_labels, rails = labelled + 1, max(max_labels, len(labels)), rails + len(labels)
                unbounded += sum(1 for label in labels if label not in named)
            for value in node.values():
                walk(value, path)
        elif isinstance(node, list):
            for value in node:
                walk(value, path)

    for f in files:
        text = f.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = json.loads(re.sub(r"/\*.*?\*/", "", text, flags=re.S))
            stripped += 1
        arrays += isinstance(data, list)
        walk(data, str(f.relative_to(checkout)))
    guide = (checkout / "CONFIG_FORMAT.md").read_text(encoding="utf-8")
    documented = re.findall(r'^\|\s*"(\$\w+)"\s*\|', guide, flags=re.M)
    example = {n for n in re.findall(r'"Name":\s*"([^"]*)"', guide) if re.search(r"critical|recoverable", n, re.I)}
    code = checkout / "src" / "entity_manager" / "utils.cpp"
    # The substitution builds its search string as the template character plus a property's name, for every
    # property of the matched device -- so any property is a template, not only the ones the guide lists.
    any_property = bool(re.search(r"templateChar\s*\+\s*propName", code.read_text(encoding="utf-8"))) \
        if code.exists() else None
    schema = json.loads((checkout / "schemas" / "legacy.json").read_text(encoding="utf-8"))
    item = schema.get("$defs", {}).get("Types", {}).get("Thresholds", {}).get("items", {})
    fields = item.get("properties", {})
    return {"files": len(files), "read_after_stripping_comments": stripped, "top_level_arrays": arrays,
            "example_threshold_names": len(example), "substitutes_any_property": any_property,
            "threshold_schema_required": sorted(item.get("required", [])),
            "threshold_direction_values": sorted(fields.get("Direction", {}).get("enum", [])),
            "threshold_name_schema": sorted(f"{k}={v}" for k, v in fields.get("Name", {}).items()),
            "threshold_schema_relations": sorted(k for k in ("if", "then", "else", "dependentSchemas", "dependentRequired",
                                                             "allOf", "anyOf", "oneOf") if k in item),
            "thresholds": thresholds, "directions": dict(directions), "threshold_name_spellings": len(spellings),
            "threshold_name_counts": [f"{name}={n}" for name, n in sorted(spellings.items(),
                                                                          key=lambda kv: (-kv[1], str(kv[0])))],
            "contradictions": sorted(contradictions), "contradiction_details": sorted(details),
            "entries_with_labels": labelled, "max_labels": max_labels,
            "rails": rails, "rails_without_threshold": unbounded,
            "template_strings_documented": sorted(s.lower() for s in documented)}


def reader_python(spec: str, *pins: str) -> Path:
    """The interpreter of a virtualenv holding exactly `spec` from PyPI, and any further pins, made once and kept."""
    return venv_python(spec, *pins)


def venv_python(*specs: str) -> Path:
    """The interpreter of a virtualenv holding exactly these pins from PyPI, made once and kept."""
    pins = []
    for spec in specs:
        name, _, version = spec.partition("==")
        if not version:
            raise SystemExit(f"an exact pin is NAME==VERSION, not {spec!r}")
        pins.append((re.sub(r"\[.*\]$", "", name), version))
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "arbiter-report-measure"
    venv = cache / re.sub(r"[^A-Za-z0-9._+-]", "-", "+".join(sorted(specs)))
    python = venv / "bin" / "python"
    check = [str(python), "-c", "import importlib.metadata as m; "
             f"print(all(m.version(n) == v for n, v in {pins!r}))"]
    if python.exists() and subprocess.run(check, capture_output=True, text=True).stdout.strip() == "True":
        return python
    for make in ([sys.executable, "-m", "venv", str(venv)], [sys.executable, "-m", "virtualenv", "-q", str(venv)]):
        shutil.rmtree(venv, ignore_errors=True)   # a failed attempt leaves a virtualenv without pip
        if subprocess.run(make, capture_output=True).returncode == 0 and (venv / "bin" / "pip").exists():
            break
    else:
        raise SystemExit(f"could not make a virtualenv at {venv}: neither venv nor virtualenv worked")
    subprocess.run([str(venv / "bin" / "pip"), "install", "-q", "--disable-pip-version-check", *specs], check=True)
    return python


def census_with(spec: str, checkout: Path, pins: tuple = ()) -> dict:
    """The released tool's `census --json` over the checkout, flattened under `census.`."""
    tool = venv_python(spec, *pins).parent / "bmc-sensor-audit"
    done = subprocess.run([str(tool), "census", str(checkout / "configurations"), "--json"], capture_output=True,
                          text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if done.returncode:
        raise SystemExit(f"the census of {spec} exited {done.returncode}:\n{done.stderr}")
    census, flat = json.loads(done.stdout), {}

    def walk(prefix: str, node) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(f"{prefix}.{key}", value)
        else:
            flat[prefix] = node
    walk("census", census)
    flat["census.contradictions"] = sorted(f"configurations/{c['file']}:{c['label']}={c['value']}"
                                           for c in census["thresholds"]["name_contradicts_direction"])
    by_type = census["declarations"]["by_type"]
    flat["census.not_a_sensor_types"] = len(by_type["not_a_sensor"])
    flat["census.unrecognised_types"] = len(by_type["unrecognised"])
    flat["census.threshold_name_spellings"] = len(census["thresholds"]["by_name"])
    flat["census.template_variables_used"] = sorted(census["declarations"]["template_variables"])
    # Appendix A's tables, in the census's own order: largest first, then by name.
    flat["census.threshold_name_counts"] = [f"{name}={n}" for name, n in census["thresholds"]["by_name"].items()]
    flat["census.not_a_sensor_top10"] = [f"{name}={n}" for name, n in list(by_type["not_a_sensor"].items())[:10]]
    flat["census.unrecognised_by_type"] = [f"{name}={n}" for name, n in by_type["unrecognised"].items()]
    return flat


def read_with(spec: str, checkout: Path, pins: tuple = ()) -> dict:
    done = subprocess.run([str(reader_python(spec, *pins)), "-c", READER_PASS, str(checkout)], capture_output=True,
                          text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if done.returncode:
        raise SystemExit(f"the reader {spec} failed:\n{done.stderr}")
    return {"reader": spec, **json.loads(done.stdout)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rev", required=True, help="the entity-manager revision the report names")
    ap.add_argument("--checkout", type=Path, help="an existing checkout AT that revision")
    ap.add_argument("--expect-files", type=int)
    ap.add_argument("--expect-thresholds", type=int)
    ap.add_argument("--expect-direction", action="append", default=[], metavar="'VALUE=N'")
    ap.add_argument("--expect-contradiction", action="append", default=[], metavar="PATH:LABEL=VALUE")
    ap.add_argument("--reader", metavar="'bmc-sensor-audit==VERSION'",
                    help="also read the checkout with this released version of the audit tool")
    ap.add_argument("--census", metavar="'bmc-sensor-audit==VERSION'",
                    help="also run this released version's own census over the checkout (0.3.19 and later)")
    ap.add_argument("--expect", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--pin", action="append", default=[], metavar="'NAME==VERSION'",
                    help="pin a further package beside the released tool, e.g. the library it shares")
    args = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        checkout = args.checkout or fetch(args.rev, Path(tmp))
        head = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"], capture_output=True,
                              text=True).stdout.strip()
        if not head.startswith(args.rev):
            print(f"the checkout is at {head or 'no git revision'}, not {args.rev}", file=sys.stderr)
            return 2
        committed = subprocess.run(["git", "-C", str(checkout), "log", "-1", "--format=%cI", "HEAD"],
                                   capture_output=True, text=True).stdout.strip()[:10]
        result = {"rev": head, "committed": committed, **measure(checkout),
                  **(read_with(args.reader, checkout, tuple(args.pin)) if args.reader else {}),
                  **(census_with(args.census, checkout, tuple(args.pin)) if args.census else {})}
    print(json.dumps(result, indent=1, sort_keys=True))
    wrong = []
    if args.expect_files is not None and result["files"] != args.expect_files:
        wrong.append(f"files {result['files']}, expected {args.expect_files}")
    if args.expect_thresholds is not None and result["thresholds"] != args.expect_thresholds:
        wrong.append(f"thresholds {result['thresholds']}, expected {args.expect_thresholds}")
    for pair in args.expect_direction:
        value, _, n = pair.rpartition("=")
        if result["directions"].get(value) != int(n):
            wrong.append(f"Direction {value!r} {result['directions'].get(value)}, expected {n}")
    if args.expect_contradiction and sorted(args.expect_contradiction) != result["contradictions"]:
        wrong.append(f"contradictions {result['contradictions']}, expected {sorted(args.expect_contradiction)}")
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
