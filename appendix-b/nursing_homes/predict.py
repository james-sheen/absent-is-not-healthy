"""Write the nursing homes case study's answers, before any walk is run: `answers.json`.

    python3 predict.py

The answers are what the model, read by the rules the engine's modelling guide states, should make
the engine say about each capture. This file does not import the engine: it is a second reading of the same
rules, written down first, so a difference with the run is either a misreading here or a defect there -- and
STORY.md says which, after. It is the unemployment case's `predict.py`, taught upper lines on counts, lines read
off a unit that move (SSA's), lines that are there only in some months, and a cause reached through another.

The rules applied, as the spec and the engine's own documentation state them:
- BOUNDEDNESS on an upper line: a reading at or above `warning` is a warning; on a lower line, a reading at or
  below `lower_warning` -- a reading ON a line is across it. A line read off the unit (`{from_property: ...}`) is
  the unit's value that month; where the unit carries none, the check declines `no_threshold`, a decline a
  declaration would cure and no reading. With no current value the check declines `no_current_value`, or
  `missing_property` on a unit that never held it. A one-day window holds one reading, so no trend is projected.
- HOMEOSTASIS on a unit that never held the value declines `missing_property`.
- STABILITY on a STATE reading: a current value in `bad:` is a finding at HIGH; the oscillation arm declines
  below 10 state readings.
- An entity is faulty with a finding at the evidence floor; unread when no check on it ran; partial when one
  ran and a decline a reading would cure stands (`insufficient_samples`, `missing_property`,
  `no_current_value`, `missing_entity_type` -- the engine's `DECLINE_REMEDY`); clean otherwise.
- A walk climbs declared causal edges -- the source of an edge is a cause of its target -- within three hops:
  a cause reached through causes that are not clean is on the trail (faulty) or open (partial or unread); a
  cause reached only through a clean one, or clean itself, is screened; a trail cause with nothing above it
  that is not clean is the frontier. Causes rank by standing, then hops, then id. `cut`, `traced`,
  `partly_traced`, `open`, `unexplained` as the VA case states them. The reading a walk names: of the open
  causes, the one alone (`only_candidate` when it is the walk's only cause, `only_open` otherwise), or the one
  whose reading, were it clean, would screen the most other causes (`screening`, with the count); its first
  declared value a reading would cure.
- A plan with no lever has nothing to choose between: the plan leg ranks nothing and declines `no_candidates`.
- A case opens on a finding, and closes after three checks in a row that looked and found nothing at or above
  a warning; a check that declined -- every axiom on the indicator -- restarts the count, except one whose only
  want is a line the unit no longer carries while its reading is there, which counts toward closing as a clean
  one does (from 0.2.39, since this file first ran: the run held 232 cases open on lines a court had struck down).
  A case closed on a declared line says what crossed: the reading, when the closing reading is inside the line
  it was last found against; the line, when the reading it was last found at is inside the closing line; both,
  when each would alone, or only the two did (from 0.2.39); and a case closed by a check whose line was withdrawn
  says `withdrawn`, with the line it was last found against and none after. Other cases say nothing.
- A retired unit (from 0.2.39) is no longer checked, walked or reached from its capture on; each case open on it
  resolves at that capture, saying so (`resolved_by: {by: retired, basis}`). Retirement comes before the check.
- No report names a home and a cause, so nothing is confirmed.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
STABILITY_WINDOW, MAX_HOPS, CASE_CHECKS = 10, 3, 3
WORKFORCE, EVENT = "ne-nursing-workforce", "ev-covid-19"
#: Each home's checked readings: the line it is judged against, as (kind of line, a number or the property it is
#: read off).
LINES = {"days_rn_under_8h": ("warning", 1),
         "days_licensed_under_24h": ("warning", 1),
         "days_without_rn_in_quarter": ("warning", "one_star_days"),
         "total_nurse_hprd": ("lower_warning", "min_total_hprd"),
         "rn_hprd": ("lower_warning", "min_rn_hprd"),
         "aide_hprd": ("lower_warning", "min_aide_hprd")}
#: The model's causal rules, as (relation, source type, target type).
RULES = [("staffs", "Workforce", "NursingHome"), ("strains", "Event", "Workforce")]
#: The values each type declares, in the model's order.
DECLARED = {"NursingHome": list(LINES), "Workforce": ["nurses_available"], "Event": ["national_emergency"]}
CURABLE = ("insufficient_samples", "missing_property", "no_current_value", "missing_entity_type")


def load():
    return [json.loads(p.read_text()) for p in sorted((HERE / "captures").glob("20*.json"))]


def instant(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)


def standings(subject, parents, state):
    """hops and standing of every cause a walk from `subject` reaches."""
    hops, routes = {}, {}
    layer = [(subject, 0, True)]
    while layer:
        nxt = []
        for node, depth, open_route in layer:
            if depth == MAX_HOPS:
                continue
            for cause in parents.get(node, []):
                through = open_route and (node == subject or state[node] != "clean")
                if cause not in hops or depth + 1 < hops[cause]:
                    hops[cause] = depth + 1
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
    return hops, standing


ORDER = {"frontier": 0, "trail": 1, "open": 2, "screened": 3}


def inside(reading, bounds):
    """Whether `reading` is inside every line `bounds` holds, a reading ON a line being across it."""
    if not bounds:
        return None
    return all(reading > b if line.startswith("lower_") else reading < b for line, b in bounds.items())


def resolution(found, closing):
    """From 0.2.39: `(reading, bounds)` when the case was last found and when it closed -> what crossed."""
    (r0, before), (r1, after) = found, closing
    if inside(r0, before) is not False or inside(r1, after) is not True:
        return None
    by_reading, by_line = inside(r1, before), inside(r0, after)
    by = "reading" if by_reading and not by_line else "bound" if by_line and not by_reading else "both"
    return {"by": by, "reading": [r0, r1],
            "bounds": {line: [before.get(line), after.get(line)] for line in sorted(set(before) | set(after))}}


def gone(found, reading):
    """From 0.2.39: `(reading, bounds)` when the case was last found, and the reading the withdrawn line left."""
    r0, before = found
    return {"by": "withdrawn", "reading": [r0, reading], "bounds": {line: [b, None] for line, b in before.items()}}


def main() -> int:
    caps = load()
    months = [c["month"] for c in caps]
    types = {u["name"]: u["type"] for u in caps[0]["units"]}
    parents: dict = {}
    arriving: dict = {}
    for u in caps[0]["units"]:
        for relation, targets in u["edges"].items():
            for target in targets:
                parents.setdefault(target, []).append(u["name"])
                arriving[(target, relation)] = arriving.get((target, relation), 0) + 1
    emergency: list = []
    held: set = set()                          # (entity, value) a unit has ever held
    answers = {"findings": {}, "states": {}, "walks": {}, "plan": {}, "gaps": {}, "cases": [],
               "confirmations": []}
    open_cases, clean_run, book, last_found = {}, {}, [], {}

    for cap, month in zip(caps, months):
        # From 0.2.39, a home CMS no longer lists leaves at the capture that retires it, its open cases with it.
        for u in cap["units"]:
            if u.get("retired"):
                for key in [k for k in open_cases if k[0] == u["name"]]:
                    case = open_cases.pop(key)
                    case["resolved"] = month
                    case["resolved_by"] = {"by": "retired", "basis": u.get("retired_basis") or ""}
        values = {u["name"]: u["values"] for u in cap["units"] if not u.get("retired")}
        findings, declined, ran, judged, withdrawn = {}, {}, {}, {}, {}

        def find(entity, indicator, severity):
            findings.setdefault(entity, {})[indicator] = severity

        def decline(entity, indicator, reason):
            declined.setdefault(entity, {})[indicator] = reason

        def absent(entity, indicator):
            decline(entity, indicator, "no_current_value" if (entity, indicator) in held else "missing_property")

        for name, v in values.items():
            for indicator in v:
                held.add((name, indicator))
            kind = types[name]
            if kind == "NursingHome":
                for indicator, (side, line) in LINES.items():
                    if indicator not in v:
                        absent(name, indicator)
                        continue
                    if isinstance(line, str):
                        if line not in v:
                            decline(name, indicator, "no_threshold")
                            withdrawn[(name, indicator)] = v[indicator]
                            continue
                        line = v[line]
                    ran[name] = ran.get(name, 0) + 1
                    reading = v[indicator]
                    judged[(name, indicator)] = (reading, {side: line})
                    if (reading >= line) if side == "warning" else (reading <= line):
                        find(name, indicator, "warning")
            elif kind == "Workforce":
                absent(name, "nurses_available")
            elif kind == "Event":
                emergency.append(v["national_emergency"])
                if len(emergency) < STABILITY_WINDOW:
                    decline(name, "national_emergency", "insufficient_samples")
                else:
                    ran[name] = ran.get(name, 0) + 1
                if v["national_emergency"] == "declared":
                    find(name, "national_emergency", "high")
        state = {}
        for n in values:
            if n in findings:
                state[n] = "faulty"
            elif not ran.get(n):
                state[n] = "unread"
            elif any(r in CURABLE for r in declined.get(n, {}).values()):
                state[n] = "partial"
            else:
                state[n] = "clean"
        answers["findings"][month] = {n: sorted(f) for n, f in sorted(findings.items())}
        answers["states"][month] = {n: s for n, s in sorted(state.items()) if s != "clean"}

        # -- the walks: one per entity with a finding ------------------------------------------------
        walks = {}
        for subject in sorted(findings):
            hops, standing = standings(subject, parents, state)
            ranking = sorted(hops, key=lambda c: (ORDER[standing[c]], hops[c], c))
            has = {s: any(x == s for x in standing.values()) for s in ORDER}
            walk_state = ("cut" if not hops else
                          "traced" if has["frontier"] and not has["open"] else
                          "partly_traced" if has["frontier"] else
                          "open" if has["open"] else "unexplained")
            opened = [c for c in ranking if standing[c] == "open"]
            named = None
            if opened:
                screens = None
                if len(opened) == 1:
                    pick, basis = opened[0], ("only_candidate" if len(hops) == 1 else "only_open")
                else:
                    def screened_if_clean(c):
                        _hops, after = standings(subject, parents, {**state, c: "clean"})
                        return sum(1 for o in after if o != c and after[o] == "screened"
                                   and standing[o] != "screened")
                    counts = {c: screened_if_clean(c) for c in opened}
                    best = max(counts.values())
                    pick, basis = next(c for c in opened if counts[c] == best), "screening"
                    screens = best
                untaken = [p for p in DECLARED[types[pick]]
                           if p in declined.get(pick, {}) and declined[pick][p] in CURABLE]
                named = {"entity": pick, "reading": f"{pick}.{untaken[0]}" if untaken else None, "basis": basis}
                if screens is not None:
                    named["screens"] = screens
            walks[subject] = {"state": walk_state, "ranking": ranking, "standing": standing,
                              "most_discriminating": named}
        answers["walks"][month] = walks

        # -- the plan: no lever, nothing to choose between -----------------------------------------------
        answers["plan"][month] = {"best": [], "ranked": False, "declined": ["no_candidates"]}

        # -- what the declaration cannot explain ----------------------------------------------------
        gaps: dict = {}
        for subject, walk in walks.items():
            if walk["state"] == "unexplained":
                gaps.setdefault("unexplained_finding", set()).add(subject)
            reached = [subject] + [c for c, s in walk["standing"].items() if s == "frontier"]
            for entity in reached:
                for relation, _source, target in RULES:
                    if types[entity] == target and not arriving.get((entity, relation)):
                        gaps.setdefault("no_cause_connected", set()).add(entity)
        answers["gaps"][month] = {kind: sorted(at) for kind, at in sorted(gaps.items())}

        # -- cases -----------------------------------------------------------------------------------------
        indicators = {(n, i) for n, f in findings.items() for i in f}
        for key in sorted(indicators):
            if key not in open_cases:
                again = any(c["key"] == list(key) for c in book)
                open_cases[key] = {"key": list(key), "opened": month, "resolved": None, "reopened": again,
                                   "resolved_by": None}
                book.append(open_cases[key])
                clean_run[key] = 0
            if key in judged:
                last_found[key] = judged[key]
        for key in list(open_cases):
            if key in indicators:
                clean_run[key] = 0
            elif key[1] in declined.get(key[0], {}) and key not in withdrawn:
                clean_run[key] = 0
            else:
                clean_run[key] += 1
                if clean_run[key] >= CASE_CHECKS:
                    case = open_cases.pop(key)
                    case["resolved"] = month
                    if key in withdrawn:
                        case["resolved_by"] = gone(last_found[key], withdrawn[key])
                    elif key in judged:
                        case["resolved_by"] = resolution(last_found[key], judged[key])
    answers["cases"] = book
    answers["book"] = {"opened": len(book), "resolved": sum(1 for c in book if c["resolved"]),
                       "open": sum(1 for c in book if not c["resolved"]),
                       "reopened": sum(1 for c in book if c["reopened"]),
                       "resolved_by": {by: sum(1 for c in book if (c["resolved_by"] or {}).get("by") == by)
                                       for by in ("reading", "bound", "both", "withdrawn", "retired")}}
    (HERE / "answers.json").write_text(json.dumps(answers, indent=1, sort_keys=True) + "\n")
    print(f"{len(months)} captures, {months[0]}..{months[-1]}; {len(book)} cases; book {answers['book']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
