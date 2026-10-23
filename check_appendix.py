#!/usr/bin/env python3
"""Run one of appendix B's cases on the released engine, as a reader of the repository would, and hold it to its answers.

    check_appendix.py CASE_DIR --engine 'arbiter-engine==VERSION'

The engine is installed from PyPI into a virtualenv of its own, the one `measure_corpus.py` makes and keeps. The
case's runner writes its results into a fresh directory, never the case's own, with the published engine; its
scorer -- which holds a run to the answers written before the engine ran and fails on any departure -- then reads
them, and its exit status is this script's. A case that reproduces exits 0.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_corpus import venv_python  # noqa: E402

# How each case's scorer takes the results it reads.
SCORER_ARGS = {"faa": ["--results", "{results}"], "nursing_homes": ["{results}"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case", type=Path, help="the case's folder: its runner, scorer, answers and captures")
    ap.add_argument("--engine", required=True, metavar="'arbiter-engine==VERSION'")
    args = ap.parse_args(argv)
    case = args.case.resolve()
    if case.name not in SCORER_ARGS:
        print(f"no scorer is known for {case.name!r}", file=sys.stderr)
        return 2
    python = str(venv_python(args.engine))
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    with tempfile.TemporaryDirectory() as out:
        ran = subprocess.run([python, "run_walks.py", "--out", out, "--engine", "published"], cwd=case, env=env,
                             capture_output=True, text=True)
        if ran.returncode:
            print(ran.stdout[-1500:], ran.stderr[-1500:], sep="\n", file=sys.stderr)
            return ran.returncode
        results = str(Path(out) / "results.json")
        scored = subprocess.run([python, "score.py", *(a.format(results=results) for a in SCORER_ARGS[case.name])],
                                cwd=case, env=env, capture_output=True, text=True)
    print(ran.stdout.strip().splitlines()[0] if ran.stdout.strip() else "")
    print(scored.stdout.strip()[-1500:])
    if scored.returncode:
        print(scored.stderr[-1500:], file=sys.stderr)
    return scored.returncode


if __name__ == "__main__":
    sys.exit(main())
