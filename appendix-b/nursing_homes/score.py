"""Hold a run of the nursing homes case study (`results.json`) to the answers written before it.

    python3 score.py [results.json]

Every answer `predict.py` wrote is compared field by field with what the engine said, and each departure
is printed with the month it happened in. A count of agreements says nothing on its own: read the
departures. The unemployment case's `score.py`; nothing is confirmed here, so a confirmation is a departure.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def kind_of(subject: str) -> str:
    return "event" if subject.startswith("ev-") else "workforce" if subject.startswith("ne-") else "home"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    run = json.loads(Path(argv[0] if argv else HERE / "results.json").read_text())
    answers = json.loads((HERE / "answers.json").read_text())
    tally, departures = Counter(), defaultdict(list)

    def hold(kind, where, said, expected):
        tally[(kind, said == expected)] += 1
        if said != expected:
            departures[kind].append((where, expected, said))

    for record in run["months"]:
        month = record["month"]
        found = defaultdict(set)
        for entity, indicator, _severity in record["findings"]:
            found[entity].add(indicator)
        hold("findings", month, {e: sorted(i) for e, i in sorted(found.items())}, answers["findings"][month])
        expected_walks = answers["walks"][month]
        for subject in sorted(set(expected_walks) | set(record["walks"])):
            exp, got = expected_walks.get(subject), record["walks"].get(subject)
            exp_view = exp and {"state": exp["state"], "ranking": exp["ranking"], "standing": exp["standing"]}
            got_view = got and {"state": got["state"], "ranking": got["ranking"], "standing": got["standing"]}
            hold("walk:" + kind_of(subject), f"{month} {subject}", got_view, exp_view)
            named = got and got.get("most_discriminating")
            if named:
                named = {k: named.get(k) for k in ("entity", "reading", "basis", "screens") if k in named}
            hold("named reading:" + kind_of(subject), f"{month} {subject}", named,
                 exp and exp.get("most_discriminating"))
        plan, want = record["plan"], answers["plan"][month]
        hold("plan", month, {"best": plan["best"], "ranked": plan["ranked"],
                             "declined": sorted(set(plan["declined"]) & set(want["declined"]))},
             {k: want[k] for k in ("best", "ranked", "declined")})
        hold("gaps", month, {k: sorted(v) for k, v in sorted(record["gaps"].items())}, answers["gaps"][month])

    book = run["book"]
    cases = book.get("cases") or []
    said = sorted((c["entity_id"], c["indicator"], (c.get("opened_at") or "")[:7],
                   (c.get("resolved_at") or "")[:7] or None) for c in cases)
    expected = sorted((c["key"][0], c["key"][1], c["opened"], c["resolved"]) for c in answers["cases"])
    for row in sorted(set(said) | set(expected)):
        hold("cases", " ".join(str(x) for x in row), row in said, row in expected)
    # What each resolved case says crossed -- the reading or the line (from 0.2.39); a case no line decided, none.
    want_by = {(c["key"][0], c["key"][1], c["opened"]): c["resolved_by"] for c in answers["cases"]}
    for c in cases:
        key = (c["entity_id"], c["indicator"], (c.get("opened_at") or "")[:7])
        if key in want_by:
            hold("what a resolved case says crossed", " ".join(key), c.get("resolved_by"), want_by[key])
    for key in ("opened", "resolved", "open", "reopened", "resolved_by"):
        hold("book " + key, "all", book.get(key), answers["book"][key])
    print("cases: run", len(said), "answers", len(expected), "| book counts:",
          {k: book.get(k) for k in ("opened", "resolved", "open", "reopened", "resolved_by")})

    # Nothing is confirmed: no report names a home and a cause.
    for row in (book.get("confirmed") or {}).get("rows") or []:
        hold("confirmations", "extra", row, None)
    print("confirmed counts:", {k: v for k, v in (book.get("confirmed") or {}).items() if k != "rows"})

    print("\nagreements by kind:")
    for kind in sorted({k for k, _ in tally}):
        print(f"  {kind:34s} {tally[(kind, True)]:5d} held  {tally[(kind, False)]:5d} departed")
    for kind, rows in departures.items():
        print(f"\n== {kind}: {len(rows)} departures; the first eight")
        for where, exp, got_ in rows[:8]:
            print(f"  {where}\n     answer: {json.dumps(exp, default=str)[:400]}\n"
                  f"     run:    {json.dumps(got_, default=str)[:400]}")
    return 1 if departures else 0              # a departure fails the run, so a CI step cannot pass over one


if __name__ == "__main__":
    raise SystemExit(main())
