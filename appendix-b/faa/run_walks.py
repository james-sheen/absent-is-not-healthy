"""Run the FAA case study offline, and hold it to `answers.json`.

    python3 run_walks.py [--out DIR] [--engine published|tree]

`--engine published` runs the walk on `arbiter-engine` as PyPI installs it; `tree` runs it on the engine in the
source tree, where there is one (`case_engine.py`).

One session, fed the way a yearly review is fed: the facilities and the FAA with their links, then
each capture in turn -- its counts as the units' current state, the same counts as readings at the
capture's instant -- and after each the walk (`walks.py`'s `run`), which checks, opens cases, ranks
causes, plans and lists what the declaration cannot explain. No decision is filed: the model declares
no flow out of training, so a forecast of what hiring did could be graded only against a world without
the year's 1,460 losses. No LLM, and no service: the engine in-process.

Writes `results.json` (one compact record a year, and the case book) to --out; `score.py` holds it to
the answers.
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

YEARS = ("2023-09", "2024-09", "2025-09")


def instant(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)


def compact_walk(envelope: dict) -> dict:
    hypothesis = envelope.get("hypothesis") or {}
    walk = hypothesis.get("walk") or {}
    candidates = hypothesis.get("candidates") or []
    return {"state": walk.get("state"), "ranking": [c.get("cause") for c in candidates],
            "standing": {c.get("cause"): c.get("standing") for c in candidates}}


def compact_plan(envelope: dict) -> dict:
    plan = envelope.get("plan") or {}
    candidates = plan.get("candidates") or []

    def label(candidate: dict) -> list:
        return [f"{a.get('template')}@{a.get('entity_id')}" for a in candidate.get("actions") or []] or ["nothing"]
    best = next((c for c in candidates if c.get("plan") == plan.get("best")), None)
    return {"best": label(best) if best else [], "objective": plan.get("objective"),
            "candidates": [[label(c), c.get("objective")] for c in candidates],
            # From 0.2.39, the lines each option's writes move.
            "moves_bounds": {" + ".join(label(c)): c.get("moves_bounds") or [] for c in candidates},
            "declined": [n.get("reason") for n in envelope.get("not_checked") or []][:6]}


def compact_gaps(envelope: dict) -> dict:
    out: dict = {}
    for row in (envelope.get("residuals") or {}).get("hypotheses") or []:
        where = row.get("at") or row.get("on") or row.get("between")
        out.setdefault(row.get("kind"), []).append(where if isinstance(where, str) else json.dumps(where))
    return {kind: sorted(set(v)) for kind, v in out.items()}


def indicator_of(problem_type: str) -> str:
    return problem_type.split(":", 1)[-1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=HERE)
    ap.add_argument("--engine", choices=case_engine.ENGINES, default=case_engine.DEFAULT)
    args = ap.parse_args(argv)
    api, walks, InMemoryObservationHistory = case_engine.load(args.engine)
    print(f"engine: {case_engine.describe(args.engine, api)}", flush=True)
    captures = [json.loads((HERE / "captures" / f"{y}.json").read_text()) for y in YEARS]
    session = api.EngineSession(history=InMemoryObservationHistory(
        retention_period=timedelta(days=1500), max_observations_per_key=100))
    session.load_model((HERE / "model.yaml").read_text())
    for unit in captures[0]["units"]:
        session.add_entity(unit["name"], unit["type"], properties={}, name=unit.get("label") or unit["name"])
    for unit in captures[0]["units"]:
        for relation, targets in unit["edges"].items():
            for target in targets:
                session.add_relationship(unit["name"], relation, target)

    records, started = [], time.time()
    for capture in captures:
        year, at = capture["captured_at"][:7], instant(capture["captured_at"])
        for unit in capture["units"]:
            session.entities[unit["name"]].properties = dict(unit["values"])
            for prop, value in unit["values"].items():
                session.add_observations(unit["name"], prop, [(at, value)])
        out = walks.run(api, session, as_of=at)
        findings: dict = {}
        for f in out["findings"]:
            findings.setdefault(f["entity_id"], {})[indicator_of(f["problem_type"])] = f.get("severity")
        records.append({
            "year": year,
            "findings": {k: findings[k] for k in sorted(findings)},
            "problem_types": sorted({f["problem_type"].split(":", 1)[0] for f in out["findings"]}),
            "walks": {unit: compact_walk(env) for unit, env in sorted(out["upward"].items())},
            "plan": compact_plan(out["downward"]),
            "gaps": compact_gaps(out["between"]),
            "cases": {k: v for k, v in (out.get("cases") or {}).items() if k != "by_finding"},
            "not_checked": sorted({(n.get("reason") or "") for n in out.get("not_checked") or []}),
        })
        print(f"  {year}: {len(out['findings'])} findings, {time.time() - started:.0f} s", flush=True)
    book = walks.book(api, session)
    cases = [{k: c.get(k) for k in ("case_id", "entity_id", "indicator", "opened_at", "resolved_at", "status",
                                    "severity", "consecutive_checks", "opened_with", "resolved_by")}
             | {"checks": [{k: e.get(k) for k in sorted(e) if k != "seq"} for e in (c.get("stages") or {}).get("check") or []],
                "stages": {s: len(v) for s, v in (c.get("stages") or {}).items()}}
             for c in book.get("cases") or []]
    result = {"elapsed_s": round(time.time() - started, 1), "years": records,
              "book": {k: book.get(k) for k in ("opened", "resolved", "open", "reopened", "resolved_by")},
              "cases": cases}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(json.dumps(result, indent=1, sort_keys=True, default=str) + "\n")
    print(f"{len(records)} years in {result['elapsed_s']} s -> {args.out / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
