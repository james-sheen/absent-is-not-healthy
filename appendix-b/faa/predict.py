"""Write the FAA case study's answers, before any walk is run: `answers.json`.

    python3 predict.py

The answers are what the model, read by the rules the engine's modelling guide states,
should make the engine say about each year's capture. This file does not import the engine: it is
a second reading of the same rules, written down first, so a difference with the run is either a
misreading here or a defect there -- and STORY.md says which, after.

The rules applied, as the spec states them:
- BOUNDEDNESS fires AT a floor (inclusive): at or below `lower_critical` is critical, else at or
  below `lower_warning` a warning. Here both floors are read off the unit: one short of its target,
  and the largest whole number under 85 percent of it, `(17 * target - 1) // 20`. A reading that
  is missing declines (`no_current_value`).
- An entity is faulty with a finding at the evidence floor (every severity here), partial when
  nothing was found and a check declined, clean otherwise.
- A walk climbs declared causal edges -- a facility's cause is the FAA (`cause: target`), the FAA's
  is its hiring (`feeds`) -- within two hops. A cause reached through causes that are not clean is
  on the trail when it is faulty and something above it is not clean, on the frontier when it is
  faulty and nothing above it is, open when it is partial; a cause reached only through a clean
  one, or clean itself, is screened. Without strengths, causes rank by standing, hops, then id.
  The walk is traced with a frontier and nothing open, partly traced with both, open with only
  open causes, and unexplained with neither.
- A case is the problem `cases.severity` names: it opens on a finding at or above it -- critical,
  below the placement line -- and closes after `consecutive_checks` (one) checks in a row that
  looked and found nothing at or above it. A warning alone is such a clean check. A case on a
  unit whose earlier case there resolved is a reopening.
- A plan ranks by the cost of the findings each rollout leaves (1 / priority: critical 1, warning
  1/3); a lever that leaves the same findings as doing nothing gains nothing, and ties go to fewer
  actions. Hiring writes trainees, which nothing judges; adopting the staffing model sets the FAA's
  target to 12,563, which moves the FAA's floors and nobody's count.

And the case's own question. Until 0.2.39 no field of the engine answered it: the book kept, per
check, when it ran, what it found and whether it was clean -- no reading and no bound. Now a check
records the reading and the lines it was judged against, and a resolved case says what crossed
(`resolved_by`), read off the last check that found it -- or what it opened on -- and the check
that closed it: the reading crossed the line when the closing count is above the old floor, the
line crossed the reading when the old count is above the new floor, both when each would alone, or
only the two together did. A critical case is held to its critical line alone, here the placement
line. And a plan marks the option whose write reaches a line (`moves_bounds`): the staffing model
writes the FAA's target, which both its floors are computed from; hiring writes trainees, which no
line reads. `closed_in_2025` keeps the earlier reading of the data -- which moved at all -- beside it.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
YEARS = ("2023-09", "2024-09", "2025-09")
AGENCY, HIRING = "faa", "faa-hiring"
NEW_TARGET = 12563
COST = {"warning": 1 / 3, "critical": 1.0}


def floors(target: int) -> tuple:
    """The two floors read off a unit: below its target, below 85 percent of it -- whole people."""
    return target - 1, (17 * target - 1) // 20


def band(values: dict, target: int = None):
    target = values["target"] if target is None else target
    short_of_target, short_of_line = floors(target)
    if values["cpc"] <= short_of_line:
        return "critical"
    if values["cpc"] <= short_of_target:
        return "warning"
    return None


def resolution(found: tuple, closing: tuple) -> dict:
    """As the engine reads a critical case, from 0.2.39: `(count, placement floor)` when it was last found and
    when it closed. A count ON a floor is below it, so above is strict."""
    (r0, b0), (r1, b1) = found, closing
    by_reading, by_line = r1 > b0, r0 > b1
    by = "reading" if by_reading and not by_line else "bound" if by_line and not by_reading else "both"
    return {"by": by, "reading": [r0, r1], "bounds": {"lower_critical": [b0, b1]}}


def main() -> int:
    caps = [json.loads((HERE / "captures" / f"{y}.json").read_text()) for y in YEARS]
    types = {u["name"]: u["type"] for u in caps[0]["units"]}
    parents = {}
    for u in caps[0]["units"]:
        for relation, targets in u["edges"].items():
            for target in targets:
                if relation == "belongs_to":            # cause: target -- the FAA fails the facility
                    parents.setdefault(u["name"], []).append(target)
                elif relation == "feeds":               # the hiring program feeds the FAA
                    parents.setdefault(target, []).append(u["name"])
    answers = {"findings": {}, "states": {}, "walks": {}, "plan_best": {}, "gaps": {}, "cases": [],
               "counts": {}, "closed_in_2025": {}}
    open_cases, book, found_with = {}, [], {}

    for cap, year in zip(caps, YEARS):
        values = {u["name"]: u["values"] for u in cap["units"]}
        findings, declined = {}, {}
        for name, v in values.items():
            if types[name] == "Program":
                if "hires" not in v:
                    declined.setdefault(name, set()).add("hires")
                elif v["hires"] <= v["hiring_target"] - 1:
                    findings.setdefault(name, {})["hires"] = "warning"
                continue
            b = band(v)
            if b:
                findings.setdefault(name, {})["cpc"] = b
        state = {n: ("faulty" if n in findings else "partial" if n in declined else "clean") for n in values}
        answers["findings"][year] = {n: f for n, f in sorted(findings.items())}
        answers["states"][year] = {n: s for n, s in sorted(state.items()) if s != "clean"}

        # -- the walks: one per entity with a finding --------------------------------------------
        walks = {}
        for subject in sorted(findings):
            hops, routes = {}, {}
            layer = [(subject, 0, True)]
            while layer:
                nxt = []
                for node, depth, open_route in layer:
                    if depth == 2:
                        continue
                    for cause in parents.get(node, []):
                        through = open_route and (node == subject or state[node] != "clean")
                        hops[cause] = min(hops.get(cause, depth + 1), depth + 1)
                        routes[cause] = routes.get(cause, False) or through
                        nxt.append((cause, depth + 1, through))
                layer = nxt
            standing = {}
            for cause in hops:
                if not routes[cause] or state[cause] == "clean":
                    standing[cause] = "screened"
                elif state[cause] == "faulty":
                    above = [p for p in parents.get(cause, []) if state[p] != "clean"]
                    standing[cause] = "trail" if above else "frontier"
                else:
                    standing[cause] = "open"
            order = {"frontier": 0, "trail": 1, "open": 2, "screened": 3}
            ranking = sorted(hops, key=lambda c: (order[standing[c]], hops[c], c))
            has = {s: any(v == s for v in standing.values()) for s in order}
            walks[subject] = {"state": ("cut" if not hops else
                                        "traced" if has["frontier"] and not has["open"] else
                                        "partly_traced" if has["frontier"] else
                                        "open" if has["open"] else "unexplained"),
                              "ranking": ranking, "standing": standing}
        answers["walks"][year] = walks

        # -- the plan: the lever whose rollout leaves the cheapest findings -------------------------
        faa = values[AGENCY]
        before = COST.get(band(faa), 0)
        after = COST.get(band(faa, NEW_TARGET), 0)
        answers["plan_best"][year] = (["adopt_staffing_model@faa"] if after < before else ["nothing"])

        answers["gaps"][year] = {
            "unexplained_finding": sorted(n for n, w in walks.items() if w["state"] == "unexplained")}

        # -- cases ----------------------------------------------------------------------------------
        critical = {n for n, f in findings.items() if f.get("cpc") == "critical"}
        pair = {n: (float(v["cpc"]), float(floors(v["target"])[1])) for n, v in values.items()
                if "cpc" in v and "target" in v}
        for name in sorted(open_cases):
            if name not in critical:                  # a check that looked and found no critical
                case = open_cases.pop(name)
                case["resolved"] = year
                case["resolved_by"] = resolution(found_with.pop(name), pair[name])
        for name in sorted(critical):
            if name not in open_cases:
                again = any(c["entity"] == name for c in book)
                open_cases[name] = {"entity": name, "opened": year, "resolved": None, "reopened": again,
                                    "resolved_by": None}
                book.append(open_cases[name])
            found_with[name] = pair[name]             # the last check that found it
        facilities = {n: v for n, v in values.items() if types[n] not in ("Agency", "Program")}
        answers["counts"][year] = {
            "facilities_below_placement_line": sum(1 for v in facilities.values() if band(v) == "critical"),
            "facilities_below_target_only": sum(1 for v in facilities.values() if band(v) == "warning"),
            "facilities_at_or_above_target": sum(1 for v in facilities.values() if band(v) is None),
            "of_26_critical_facilities_below_line": sum(1 for v in facilities.values()
                                                        if v["critical"] and band(v) == "critical"),
            "faa_cpc_share_of_target": round(faa["cpc"] / faa["target"], 4),
            "faa_band": band(faa),
        }

    answers["cases"] = book
    answers["book"] = {"opened": len(book), "resolved": sum(1 for c in book if c["resolved"]),
                       "open": sum(1 for c in book if not c["resolved"]),
                       "reopened": sum(1 for c in book if c["reopened"]),
                       "resolved_by": {by: sum(1 for c in book if (c["resolved_by"] or {}).get("by") == by)
                                       for by in ("reading", "bound", "both", "withdrawn", "retired")}}
    # From 0.2.39, the option whose write reaches a line, every year: the staffing model sets the FAA's target,
    # which both its floors are computed from; hiring writes trainees, which no line reads.
    answers["plan_moves_bounds"] = {
        "adopt_staffing_model@faa": [
            {"template": "adopt_staffing_model", "entity_id": AGENCY, "indicator": "cpc", "bound": "lower_critical",
             "through": ["target", "short_of_placement_line"]},
            {"template": "adopt_staffing_model", "entity_id": AGENCY, "indicator": "cpc", "bound": "lower_warning",
             "through": ["target", "short_of_target"]}],
        "hire_controllers@faa": []}
    # The case's own question, from the data: why each case that closed in 2025 closed.
    prev = {u["name"]: u["values"] for u in caps[1]["units"]}
    last = {u["name"]: u["values"] for u in caps[2]["units"]}
    why = {"its count rose, its target did not fall": [], "both": [],
           "its target fell, its count did not rise": []}
    for c in book:
        if c["resolved"] == "2025-09":
            rose = last[c["entity"]]["cpc"] > prev[c["entity"]]["cpc"]
            fell = last[c["entity"]]["target"] < prev[c["entity"]]["target"]
            key = ("both" if rose and fell else "its count rose, its target did not fall" if rose
                   else "its target fell, its count did not rise")
            why[key].append(c["entity"])
    answers["closed_in_2025"] = {k: sorted(v) for k, v in why.items()}
    answers["the_book_tells_them_apart"] = True
    (HERE / "answers.json").write_text(json.dumps(answers, indent=1, sort_keys=True) + "\n")
    print(f"{len(YEARS)} captures; {len(book)} cases; " + "; ".join(
        f"{y}: {answers['counts'][y]}" for y in YEARS))
    print("closed in 2025:", {k: len(v) for k, v in answers["closed_in_2025"].items()},
          "| resolved_by:", answers["book"]["resolved_by"], "| plan:", answers["plan_best"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
