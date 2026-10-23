"""Run the nursing homes case study offline, and hold it to `answers.json`.

    python3 run_walks.py [--out DIR] [--engine published|tree]

`--engine published` runs the walk on `arbiter-engine` as PyPI installs it; `tree` runs it on the engine in the
source tree, where there is one (`case_engine.py`).

One session, fed the way a monthly review is fed: each capture in turn -- its values as the units' current
state, the same values as readings at the capture's instant -- and after each capture the walk (`walks.py`'s
`run`), which checks, opens cases, ranks causes, plans and lists what the declaration cannot explain. A home that
reported nothing that month holds no values, and a line that did not stand that month is not on the home; a home
CMS no longer lists is retired at the capture that says so. No report names a home and a cause, so nothing is
confirmed. No LLM, and no service: the engine in-process.

Writes `results.json` (one compact record a month, and the case book) to --out; `score.py` holds it to the
answers.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))              # the case studies, for `case_engine`

import case_engine                                # noqa: E402


def instant(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)


def compact_walk(envelope: dict) -> dict:
    hypothesis = envelope.get("hypothesis") or {}
    walk = hypothesis.get("walk") or {}
    candidates = hypothesis.get("candidates") or []
    return {
        "state": walk.get("state"),
        "ranking": [c.get("cause") for c in candidates],
        "standing": {c.get("cause"): c.get("standing") for c in candidates},
        "most_discriminating": hypothesis.get("most_discriminating"),
        "declined": [n.get("reason") for n in envelope.get("not_checked") or []][:6],
    }


def compact_plan(envelope: dict) -> dict:
    plan = envelope.get("plan") or {}
    candidates = plan.get("candidates") or []

    def label(candidate: dict) -> list:
        return [f"{a.get('template')}@{a.get('entity_id')}" for a in candidate.get("actions") or []] \
            or ["nothing"]
    best = next((c for c in candidates if c.get("plan") == plan.get("best")), None)
    declined = (envelope.get("not_checked") or []) + (plan.get("not_checked") or [])
    return {"best": label(best) if best else [], "ranked": plan.get("ranked"),
            "objective": plan.get("objective"),
            "candidates": [[label(c), c.get("objective")] for c in candidates][:5],
            "declined": sorted({n.get("reason") for n in declined})}


def compact_gaps(envelope: dict) -> dict:
    out: dict = {}
    for row in (envelope.get("residuals") or {}).get("hypotheses") or []:
        where = row.get("at") or row.get("on") or row.get("between")
        out.setdefault(row.get("kind"), []).append(where if isinstance(where, str) else json.dumps(where))
    return {kind: sorted(set(v)) for kind, v in out.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=HERE)
    ap.add_argument("--engine", choices=case_engine.ENGINES, default=case_engine.DEFAULT)
    args = ap.parse_args(argv)
    api, walks, InMemoryObservationHistory = case_engine.load(args.engine)
    print(f"engine: {case_engine.describe(args.engine, api)}", flush=True)
    captures = [json.loads(p.read_text()) for p in sorted((HERE / "captures").glob("20*.json"))]

    session = api.EngineSession(history=InMemoryObservationHistory(
        retention_period=timedelta(days=9500), max_observations_per_key=10_000))
    session.load_model((HERE / "model.yaml").read_text())
    for unit in captures[0]["units"]:
        session.add_entity(unit["name"], unit["type"], properties={}, name=unit.get("label") or unit["name"])
    for unit in captures[0]["units"]:
        for relation, targets in unit["edges"].items():
            for target in targets:
                session.add_relationship(unit["name"], relation, target)

    records, started = [], time.time()
    for capture in captures:
        month, at = capture["month"], instant(capture["captured_at"])
        for unit in capture["units"]:
            if unit.get("retired"):            # from 0.2.39: a home CMS no longer lists
                with api.as_of(at):
                    api.retire_entity(session, unit["name"], basis=unit.get("retired_basis") or "")
                continue
            session.entities[unit["name"]].properties = dict(unit["values"])
            for prop, value in unit["values"].items():
                session.add_observations(unit["name"], prop, [(at, value)])
        out = walks.run(api, session, as_of=at)
        record = {
            "month": month,
            "findings": sorted({(f["entity_id"], f["problem_type"].split(":", 1)[-1], f.get("severity"))
                                for f in out["findings"]}),
            "walks": {unit: compact_walk(env) for unit, env in sorted(out["upward"].items())},
            "plan": compact_plan(out["downward"]),
            "gaps": compact_gaps(out["between"]),
        }
        records.append(record)
        if month.endswith("-09"):
            print(f"  {month}: {len(record['findings'])} findings, {len(record['walks'])} walks, "
                  f"{time.time() - started:.0f} s", flush=True)
    book = walks.book(api, session)
    cases = [{k: c.get(k) for k in ("case_id", "entity_id", "indicator", "opened_at", "resolved_at", "status",
                                    "severity", "opened_with", "resolved_by")}
             | {"stages": {s: len(v) for s, v in (c.get("stages") or {}).items()}}
             for c in book.get("cases") or []]
    result = {"elapsed_s": round(time.time() - started, 1), "months": records,
              "book": {**{k: book.get(k) for k in ("opened", "resolved", "open", "reopened", "resolved_by",
                                                  "confirmed")},
                       "cases": cases}}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(json.dumps(result, indent=1, default=str) + "\n")
    print(f"{len(records)} months in {result['elapsed_s']} s -> {args.out / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
