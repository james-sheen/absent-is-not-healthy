#!/usr/bin/env python3
"""Hold section 5 to the chain as a factory station runs it: capture, attestation, certificate, and the page.

    check_chain.py --tool 'bmc-sensor-audit[detect]==VERSION' --certificate 'odm-cert-generator[verify]==VERSION'
                   [--engine 'arbiter-engine==VERSION'] [--pin 'NAME==VERSION' ...] [--expect KEY=VALUE ...]

Both are installed from PyPI into one virtualenv of their own (the cache `measure_corpus.py` keeps), and the audit
tool's repository is cloned at the tag of the version named, for the bletchley capture and its board's
configurations. Then, in order: `detect` writes the attestation, `validate-attestation` and the certificate tool's
`check` read it, `coverage --json` gives the declaration diff, `render` builds the certificate for a unit with an
example identity, and `verify` holds the PDF to its record. The result reports each exit code; what the attestation
records; what the certificate's record holds; and what the printed page shows -- the text drawn inside the page,
told apart from text drawn beyond its edge, which a reader of the file still finds and a person does not see.

The result prints as JSON. With `--expect KEY=VALUE` it exits 0 only when every expectation holds -- the form the
report's claims ledger runs; a list compares as its items joined by commas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from measure_corpus import venv_python

TOOL_REPO = "https://github.com/james-sheen/bmc-sensor-audit"
FIXTURES = Path("tests") / "fixtures"
IDENTITY = {"serial": "EXAMPLE-0001", "work_order": "EXAMPLE-WO", "station": "EXAMPLE-STATION",
            "signer": "an example signer"}

# Run inside the virtualenv, which holds the PDF reader: every text run on each page, by where it is drawn.
PAGE_PASS = r'''
import json, sys
from pypdf import PdfReader
pages = PdfReader(sys.argv[1]).pages
inside, beyond, each = [], [], []
for page in pages:
    low, high = float(page.mediabox.bottom), float(page.mediabox.top)
    here = []
    def visit(text, cm, tm, font, size, here=here):
        if text.strip():
            y = cm[3] * tm[5] + cm[5]
            (here if low <= y <= high else beyond).append(text.strip())
    page.extract_text(visitor_text=visit)
    inside += here
    each.append(" ".join(here))
print(json.dumps({"pages": len(pages), "inside": inside, "beyond": beyond, "each": each}))
'''


def run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def chain(tool: str, certificate: str, work: Path, engine: str | None = None, pins: tuple = ()) -> dict:
    # The engine pinned beside them when named, and any further pin: `detect`'s extra and the shared core admit
    # ranges, and a fresh virtualenv after either's next release would otherwise judge with a version the report
    # does not name.
    python = venv_python(tool, certificate, *([engine] if engine else []), *pins)
    bin_ = python.parent
    version = tool.partition("==")[2]
    clone = work / "tool"
    subprocess.run(["git", "-c", "advice.detachedHead=false", "clone", "-q", "--depth", "1", "--branch",
                    f"v{version}", TOOL_REPO, str(clone)], check=True)
    here = clone / FIXTURES
    config, walk = "upstream/meta/bletchley", "walk_qemu_bletchley.json"
    attestation, coverage = work / "attestation.json", work / "coverage.json"
    record, pdf, identity = work / "certificate.json", work / "certificate.pdf", work / "identity.json"
    identity.write_text(json.dumps(IDENTITY), encoding="utf-8")

    detect = run([str(bin_ / "bmc-sensor-audit"), "detect", "--config", config, "--walk", walk,
                  "--attest-out", str(attestation)], here)
    validate = run([str(bin_ / "bmc-sensor-audit"), "validate-attestation", str(attestation)], here)
    check = run([str(bin_ / "cert-generator"), "check", str(attestation)], here)
    diff = run([str(bin_ / "bmc-sensor-audit"), "coverage", "--config", config, "--walk", walk, "--json"], here)
    coverage.write_text(diff.stdout, encoding="utf-8")
    render = run([str(bin_ / "cert-generator"), "render", "--attestation", str(attestation), "--identity",
                  str(identity), "--coverage", str(coverage), "--walk", walk, "--out-json", str(record),
                  "--out-pdf", str(pdf)], here)
    verify = run([str(bin_ / "cert-generator"), "verify", "--certificate", str(record), "--pdf", str(pdf)], here)

    a = json.loads(attestation.read_text(encoding="utf-8"))
    p12v = next(e["measurement"] for e in a["evidence"] if e["sensor"] == "P12V_AUX")
    c = json.loads(record.read_text(encoding="utf-8"))
    declared = c["not_part_of_this_judgment"]["declaration_diff"]
    source = c["source"]
    page = json.loads(run([str(python), "-c", PAGE_PASS, str(pdf)], here).stdout)
    inside, beyond = " ".join(page["inside"]), " ".join(page["beyond"])
    opening = next((t for t in page["beyond"] + page["inside"] if t.startswith("A certificate that shows only")), None)
    opening = opening.split(". ")[0] + "." if opening else None   # the first sentence; the line wraps after it
    return {
        "tool": tool, "certificate": certificate,
        "detect_exit": detect.returncode, "validate_exit": validate.returncode, "check_exit": check.returncode,
        "render_exit": render.returncode, "verify_exit": verify.returncode,
        "verify_says": verify.stdout.strip(),
        "att_format": a["format"], "att_invariants": a["checked"]["invariants"], "att_entities": a["checked"]["entities"],
        "att_findings": len(a["findings"]),
        "att_findings_by_axiom": sorted(f"{k}={n}" for k, n in Counter(f["axiom"] for f in a["findings"]).items()),
        "att_declined": len(a["not_checked"]),
        "att_declined_reasons": sorted(f"{k[0]}:{k[1]}={n}" for k, n in
                                       Counter((x["axiom"], x["reason"]) for x in a["not_checked"]).items()),
        "att_declined_details": sorted({x["detail"] for x in a["not_checked"]}),
        "att_evidence_matches_findings": len(a["evidence"]) == len(a["findings"]),
        "att_axioms": sorted({x["axiom"] for x in a["findings"] + a["not_checked"]}),
        # The checks that held: every sensor the diff matched on the machine, by its declared name, that no finding
        # names. The attestation counts its checks and lists its findings and declines; what held is the rest.
        "att_held": sorted({f["point"] for f in json.loads(coverage.read_text(encoding="utf-8"))["findings"]
                            if f.get("kind") in ("matched", "matched_inexactly")}
                           - {f["point"] for f in a["findings"]}),
        "engine_installed": run([str(python), "-c", "import importlib.metadata as m; "
                                 "print(m.version('arbiter-engine'))"], here).stdout.strip(),
        "core_installed": run([str(python), "-c", "import importlib.metadata as m; "
                               "print(m.version('presence-audit'))"], here).stdout.strip(),
        "att_lists_present": "unattested" in a and "unread_feeds" in a,
        "att_unattested": len(a.get("unattested", [])), "att_unread_feeds": len(a.get("unread_feeds", [])),
        "att_p12v_aux": f"{p12v['value']} {p12v['bound']} {p12v['threshold_type']} {p12v['threshold']}",
        "record_statement": c["judgment"]["statement"],
        "record_declared": declared["declared"], "record_declared_absent": declared["declared_absent"],
        "record_absent_named": sum("not reported at all" in json.dumps(f) for f in declared.get("findings", [])),
        "record_walk_digest_verified": source["walk_digest_verified"],
        "record_walk_digest_matches": source["walk_digest"] == "sha256:" + hashlib.sha256((here / walk).read_bytes()).hexdigest(),
        "pdf_pages": page["pages"], "pdf_runs_beyond_page": len(page["beyond"]),
        "pdf_findings_on_page": inside.count("[BOUNDEDNESS"),
        "pdf_measurements_on_page": inside.count("indicator reading"),
        "pdf_word_absent_on_page": "absent" in inside.lower(),
        "pdf_section_beyond_page": "Not part of this judgment" in beyond and "Not part of this judgment" not in inside,
        "pdf_absent_on_page": "Declared, absent" in inside, "pdf_absent_beyond_page": "Declared, absent" in beyond,
        "pdf_handle_on_page": "sha256:" in inside, "pdf_handle_beyond_page": "sha256:" in beyond,
        "pdf_section_opening": opening,
        "pdf_page_one_states_absent":
            f"{declared['declared_absent']} declared and absent" in " ".join(page["each"][0].split()),
        "pdf_pages_say_which": all(f"page {n} of {page['pages']}" in " ".join(text.split())
                                   for n, text in enumerate(page["each"], start=1)),
        "pdf_pages_name_unit": all(IDENTITY["serial"] in " ".join(text.split()) for text in page["each"]),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tool", required=True, metavar="'bmc-sensor-audit[detect]==VERSION'")
    ap.add_argument("--certificate", required=True, metavar="'odm-cert-generator[verify]==VERSION'")
    ap.add_argument("--engine", metavar="'arbiter-engine==VERSION'",
                    help="the detection engine `detect` runs, pinned rather than resolved")
    ap.add_argument("--pin", action="append", default=[], metavar="'NAME==VERSION'",
                    help="a further package pinned into the same virtualenv")
    ap.add_argument("--expect", action="append", default=[], metavar="KEY=VALUE")
    args = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        result = chain(args.tool, args.certificate, Path(tmp), args.engine, tuple(args.pin))
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
