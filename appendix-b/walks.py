"""Walk one session three ways, with the engine's own verbs.

Upward: the candidates that could explain a finding, and the one reading that would change their order. Downward:
the declared actions, ranked against the declared objective, each with what it reaches. Between: the places the
declaration cannot explain what was observed. The engine answers each -- `hypothesize`, `plan`, `gaps` -- and a case
keeps them beside the check that opened it.

NOTHING HERE COMPUTES AN ANSWER. It calls the engine's verbs in order and keeps what they return, declines included:
a model with no `planning:` block is told `no_objective`, never handed a plan.

It takes the engine module as an argument, so the same walk runs on an engine installed from the index or on one in
a source tree, and a difference between their answers is the engine's, not this file's. Standard library only.

These are the walk's own definitions, taken whole from the module that holds them alongside code serving something
else; that code is not here, and nothing here calls it.
"""
from __future__ import annotations
import copy
import importlib
import json
from contextlib import nullcontext
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

__all__ = ['run', 'book']


def case_key(finding: Mapping[str, Any]) -> Tuple[str, str]:
    """The entity and indicator a finding is about: a case follows one of each."""
    return (str(finding.get("entity_id")),
            str(finding.get("problem_type") or "").split(":", 1)[-1])


def run(api: Any, session: Any, *, as_of: Optional[datetime] = None,
        keep_cases: bool = True, book: Any = None) -> Dict[str, Any]:
    """Check, then walk: `hypothesize` once per finding's entity, `plan` and `gaps`
    once for the session, all at one instant. With `keep_cases`, open a case per
    finding the book does not hold open and attach the three walks to each case a
    finding named; the check has already recorded itself into every open case --
    the engine does that.

    THE CASES OPEN BEFORE THE WALKS, so `plan` measures each option
    against every case this check opened as well as the ones it found open: from
    engine 0.2.36 each candidate says what its rollout does to each open case,
    and opening after the plan left a session's first walk with nothing to say.
    The stages are still attached after, to every case a finding named.

    `book`, on a walk that keeps no cases, is the session's ledger: a COPY of it
    is given to the walks after the check, so they read the cases it holds while
    the check counts nothing twice -- a case counts each capture once -- and
    nothing the walks file reaches the real book.

    EACH QUESTION THE WALKS ASKED, ONCE. Every walk's envelope keeps
    the questions its inference asked, as the engine gives them; the answer here
    lists them once, in `upward_questions`, and each walk says which of them
    were its own (`_questions_once`).
    """
    clock = api.as_of(as_of) if as_of is not None else nullcontext()
    with clock:
        checked = _plain(api.check(session))
        findings = list(checked.get("findings") or [])
        judged_at = getattr(session, "_last_checked_at", None) or as_of
        if book is not None and not keep_cases:
            session.ledger = copy.deepcopy(book)
        opened = _open_cases(api, session, findings) if keep_cases else None
        upward = {unit: api.hypothesize(session, unit) for unit in _units(findings)}
        downward = api.plan(session)
        between = api.gaps(session)
        cases = (_attach(api, session, opened, upward, downward, between)
                 if keep_cases else None)
    walked = {unit: _plain(envelope) for unit, envelope in upward.items()}
    asked = _questions_once(walked)
    return {
        "judged_at": judged_at.isoformat() if isinstance(judged_at, datetime) else None,
        "findings": findings,
        "not_checked": list(checked.get("not_checked") or []),
        "checked": checked.get("checked") or {},
        "upward": walked,
        "upward_questions": asked,
        "downward": _plain(downward),
        "between": _plain(between),
        "cases": cases,
    }


def book(api: Any, session: Any) -> Dict[str, Any]:
    """Every case the session's ledger keeps, with confirmations read back."""
    return _plain(api.case_book(session)).get("cases") or {}


def _units(findings: Sequence[Mapping[str, Any]]) -> List[str]:
    """Each finding's entity once, in the order the check reported them."""
    seen: Dict[str, None] = {}
    for finding in findings:
        unit = finding.get("entity_id")
        if unit:
            seen.setdefault(str(unit), None)
    return list(seen)


def _at_case_severity(api: Any, session: Any):
    """Whether a finding is the problem the model's case criterion names: at or above
    `cases.severity`, on the engine's own scale. None when the model declares no criterion,
    and `open_case` then declines it as it did."""
    model = getattr(session, "model", None)
    severity, _count, why = model.case_criterion() if model is not None else (None, None, "no model")
    if why or not severity:
        return None
    scale = importlib.import_module(api.__name__.rsplit(".", 1)[0] + ".types").Severity
    floor = scale(severity).priority_score

    def at_or_above(finding: Mapping[str, Any]) -> bool:
        try:
            return scale(str(finding.get("severity") or "").lower()).priority_score <= floor
        except ValueError:
            return True                     # a severity off the scale is the engine's to refuse
    return at_or_above


def _open_cases(api: Any, session: Any,
                findings: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """A case per finding the book does not hold open; which case each names.

    only a finding at or above the model's case criterion opens one. A case resolves
    once `cases.consecutive_checks` checks find nothing at or above `cases.severity`, so a case
    opened on a lesser finding was read clean by its next check and resolved whatever the unit
    did, and the walk after opened it again: on the FAA case, 121 cases and 111 reopenings about
    no change at all. A lesser finding still names a case the book holds open on its indicator.
    """
    held = _held_open(session)
    the_problem = _at_case_severity(api, session)
    opened, below = 0, 0
    declined: set = set()
    by_finding: Dict[Tuple[str, str], str] = {}
    for finding in findings:
        key = case_key(finding)
        if key not in held:
            if the_problem is not None and not the_problem(finding):
                below += 1
                continue
            leg = _plain(api.open_case(session, key[0], key[1],
                                       basis=str(finding.get("problem_type") or ""))
                         ).get("case") or {}
            if not leg.get("case_id"):
                declined |= {str(d.get("reason")) for d in leg.get("not_checked") or ()
                             if d.get("reason")}
                continue
            held[key] = leg["case_id"]
            opened += 1
        by_finding[key] = held[key]
    return {"opened": opened, "declined": declined, "by_finding": by_finding,
            "below_case_severity": below}


def _held_open(session: Any) -> Dict[Tuple[str, str], str]:
    """The cases the session's book holds open, by entity and indicator.

    read off the book itself: `case_book` serializes every case, its whole history, to
    say which are open, and a walk asked it once per walk -- a quarter of a late walk on the
    longest case measured."""
    case_book = getattr(getattr(session, "ledger", None), "case_book", None)
    if case_book is None:
        return {}
    return {(case.entity_id, case.indicator): case.case_id
            for case in case_book.cases() if case.status == "open"}


def _attach(api: Any, session: Any, opened: Mapping[str, Any],
            upward: Mapping[str, Any], downward: Any, between: Any) -> Dict[str, Any]:
    """The three walks attached to each case a finding named."""
    by_finding = opened["by_finding"]
    attached: Dict[str, int] = {}
    for (unit, _indicator), case_id in sorted(by_finding.items()):
        for stage, envelope in (("hypothesize", upward.get(unit)),
                                ("plan", downward), ("gaps", between)):
            if envelope is None:
                continue
            # what was attached, not the case: three attachments a finding, each would
            # otherwise copy the case's whole history to be thrown away here.
            leg = _plain(api.attach_stage(session, case_id, stage, envelope,
                                          include_case=False)).get("case") or {}
            attached[stage] = attached.get(stage, 0) + int(
                (leg.get("checked") or {}).get("stages_attached") or 0)
    # and how many findings opened none, being below the case criterion.
    return {"opened": opened["opened"], "declined": sorted(opened["declined"]),
            "below_case_severity": opened.get("below_case_severity", 0),
            "attached": attached,
            "by_finding": [{"entity_id": k[0], "indicator": k[1], "case_id": v}
                           for k, v in sorted(by_finding.items())]}


def _questions_once(walked: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Every question the walks asked, listed once for the answer.

    A walk's inference asks, for each causal edge its answer depends on that no strength
    was declared for, how strongly a fault there breaks the next node. Where nothing
    declares a strength, every unit with a reading is evidence to every walk, so every
    walk asks about every edge of the graph: the ozone case's 1,534 in each of a week's
    285 walks, in the envelope and again in its `hypothesis` leg, 178 of the week's 198
    MB, and a Core answering the walk route encoded all of it.

    The engine's envelopes keep their questions; this answer lists each once, in
    `listed`, and each distinct list a walk asked once, in `sets`, as numbers into
    `listed`. Each walk's two lists -- the envelope's and its `hypothesis` leg's -- say
    which set was theirs and how many it held, `questions_once`, and are emptied. A set
    expanded gives a walk's list back, in its order. A walk that asked nothing is left
    as it was. `walked` is changed in place: each envelope and leg a copy, so nothing
    the engine handed over is touched.
    """
    listed: List[Dict[str, Any]] = []
    numbered: Dict[str, int] = {}
    sets: List[List[int]] = []
    set_of: Dict[Tuple[int, ...], int] = {}
    for unit in list(walked):
        envelope = dict(walked[unit])
        legs = [envelope]
        if isinstance(envelope.get("hypothesis"), dict):
            envelope["hypothesis"] = dict(envelope["hypothesis"])
            legs.append(envelope["hypothesis"])
        for leg in legs:
            questions = leg.get("questions")
            if not isinstance(questions, list) or not questions:
                continue
            numbers = []
            for question in questions:
                key = json.dumps(question, sort_keys=True, default=str)
                if key not in numbered:
                    numbered[key] = len(listed)
                    listed.append(question)
                numbers.append(numbered[key])
            if tuple(numbers) not in set_of:
                set_of[tuple(numbers)] = len(sets)
                sets.append(numbers)
            leg["questions"] = []
            leg["questions_once"] = {"set": set_of[tuple(numbers)], "count": len(numbers)}
        walked[unit] = envelope
    return {"listed": listed, "sets": sets}


def _plain(envelope: Any) -> Dict[str, Any]:
    if envelope is None:
        return {}
    if hasattr(envelope, "to_dict"):
        return envelope.to_dict()
    return dict(envelope)
