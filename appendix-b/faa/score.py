"""Hold `results.json` to `answers.json`, field by field: every departure, named.

    python3 score.py [--results FILE]

A departure is either a misreading in `predict.py` or a defect in what ran; STORY.md says which.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
YEARS = ("2023-09", "2024-09", "2025-09")


def year_of(stamp) -> str:
    return str(stamp)[:7] if stamp else None


def score(answers: dict, results: dict) -> dict:
    by_year = {r["year"]: r for r in results["years"]}
    held, departed = {}, {}

    def tally(field, year, ok, detail=None):
        held.setdefault(field, [0, 0])
        held[field][1] += 1
        if ok:
            held[field][0] += 1
        else:
            departed.setdefault(field, []).append({"year": year, **(detail or {})})

    for year in YEARS:
        run = by_year[year]
        want, got = answers["findings"][year], run["findings"]
        for entity in sorted(set(want) | set(got)):
            tally("findings", year, want.get(entity) == got.get(entity),
                  {"entity": entity, "answer": want.get(entity), "run": got.get(entity)})
        for entity, walk in answers["walks"][year].items():
            ran = run["walks"].get(entity) or {}
            for key in ("state", "ranking", "standing"):
                tally(f"walk {key}", year, walk[key] == ran.get(key),
                      {"entity": entity, "answer": walk[key], "run": ran.get(key)})
        for entity in sorted(set(run["walks"]) - set(answers["walks"][year])):
            tally("walk state", year, False, {"entity": entity, "answer": None, "run": run["walks"][entity]})
        tally("plan", year, answers["plan_best"][year] == run["plan"]["best"],
              {"answer": answers["plan_best"][year], "run": run["plan"]["best"],
               "candidates": run["plan"]["candidates"]})
        tally("gaps: unexplained_finding", year,
              answers["gaps"][year]["unexplained_finding"] == run["gaps"].get("unexplained_finding", []),
              {"answer": answers["gaps"][year]["unexplained_finding"],
               "run": run["gaps"].get("unexplained_finding", [])})
    want_cases = sorted((c["entity"], c["opened"], c["resolved"]) for c in answers["cases"])
    got_cases = sorted((c["entity_id"], year_of(c["opened_at"]), year_of(c["resolved_at"])) for c in results["cases"])
    tally("cases", "all", want_cases == got_cases,
          {"only_in_answers": sorted(set(want_cases) - set(got_cases))[:12],
           "only_in_run": sorted(set(got_cases) - set(want_cases))[:12],
           "n_answer": len(want_cases), "n_run": len(got_cases)})
    for key in ("opened", "resolved", "open", "reopened", "resolved_by"):
        tally(f"book {key}", "all", answers["book"][key] == results["book"].get(key),
              {"answer": answers["book"][key], "run": results["book"].get(key)})
    # The case's question, answered from 0.2.39: what each resolved case says crossed -- the reading or the line.
    want_by = {(c["entity"], c["opened"], c["resolved"]): c["resolved_by"] for c in answers["cases"]}
    for c in results["cases"]:
        key = (c["entity_id"], year_of(c["opened_at"]), year_of(c["resolved_at"]))
        tally("what a resolved case says crossed", key[2] or "open", want_by.get(key) == c.get("resolved_by"),
              {"case": key, "answer": want_by.get(key), "run": c.get("resolved_by")})
    for run in results["years"]:
        got = {k: v for k, v in run["plan"].get("moves_bounds", {}).items() if k != "nothing"}
        tally("the lines each option moves", run["year"], got == answers["plan_moves_bounds"],
              {"answer": answers["plan_moves_bounds"], "run": got})
    return {"held": {k: f"{a}/{b}" for k, (a, b) in held.items()}, "departed": departed}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=HERE / "results.json")
    args = ap.parse_args(argv)
    out = score(json.loads((HERE / "answers.json").read_text()), json.loads(args.results.read_text()))
    print(json.dumps(out["held"], indent=1))
    for field, rows in out["departed"].items():
        print(f"\n{field}: {len(rows)} departure(s)")
        for row in rows[:6]:
            print("  ", json.dumps(row, default=str)[:400])
    return 1 if out["departed"] else 0          # a departure fails the run, so a CI step cannot pass over one


if __name__ == "__main__":
    raise SystemExit(main())
