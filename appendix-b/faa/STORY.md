# Air traffic controllers, 2023-2025: a line that moved

A case study for *Absent is not healthy*, appendix B. Every number in it is public, and every source is named.
The answers in `answers.json` were written by `predict.py` -- which applies the specification's rules to the
captures and never imports the engine -- before the engine ran; `score.py` holds a run to them.

Its question: **can the engine tell a moved line from a mended unit?**

## What the sources say

The FAA's controller workforce plans print, for each of its 313 air traffic control facilities, a staffing target
and who is on board: certified professional controllers (CPCs), CPCs in training at a new facility (CPC-ITs), and
developmentals. Three editions give three instants:

| Edition | On board as of | Target | CPCs on board | CPCs against target |
|---|---|---:|---:|---:|
| The plan to Congress, 2024-2033 | 2023-09-23 | 14,633 (CRWG) | 10,593 | 72.4% |
| The plan for 2025-2028 | 2024-09-21 | 14,633 (CRWG) | 10,730 | 73.3% |
| The plan for 2026-2028 | 2025-09-20 | 12,563 (new staffing model) | 10,693 | 85.1% |

- **The line moved.** The 2026-2028 plan adopted a controller availability factor of 1.87 where the 2025 plan
  used 2.14, which set the total target at 12,563. 275 facility targets went down, 17 up, 21 stayed. New York
  TRACON: 113 of 226 in 2024, 112 of 160 in 2025.
- **What counts toward it moved too.** The 2023 report counted CPCs and CPC-ITs toward the target; the 2025 and
  2026 plans count CPCs. This model counts CPCs against the target in every year.
- **Two lines, both published.** The target, and 85 percent of it: the threshold the FAA and NATCA set *to
  prioritize placement of controllers at air traffic control facilities* (DOT Office of Inspector General,
  AV2023035, p. 7). The Inspector General found 20 of its 26 critical facilities below it in March 2022, and
  names them (exhibit D).
- **Hiring met its targets**: 1,811 against 1,800 in FY 2024, 2,028 against 2,000 in FY 2025. The 2026 plan says
  FY 2025's losses were 1,460, for a net gain of 568, most of it still in training.
- **The 2023 report's totals count one CPC-IT that no facility row holds**: its En Route total prints 187 CPC-ITs
  and 5,625 on board, its rows add to 186 and 5,624. Every other printed total, in every edition, equals its rows.
  The agency carries the printed totals, the facilities the rows.

## The model, in the format's own atoms

| What the case has | How the model says it |
|---|---|
| a facility, the FAA | a `Unit`; facilities typed as the 2026 plan lists them (`Center`, `Tracon`, `Tower`, `TowerTracon`, `CombinedFacility`), each `extends: Unit` |
| CPCs below the target | BOUNDEDNESS on `cpc`, `lower_warning: {from_property: short_of_target}` |
| CPCs below 85 percent of it | `lower_critical: {from_property: short_of_placement_line}` |
| *below*, for whole people | a reading on a floor is below it, so each floor is the most a unit can have and still be below its line: `target - 1`, and `(17 * target - 1) // 20` |
| hiring short of its target | BOUNDEDNESS on `hires`, floor `hiring_target - 1`; no reading for FY 2023 |
| the FAA staffs every facility | `belongs_to`, one rule per facility type, `cause: target` |
| hiring feeds the FAA | `feeds`, `edge_direction: causal` |
| the FAA's two levers | `hire_controllers` (adds 2,000 trainees) and `adopt_staffing_model` (sets the target to 12,563), on the FAA |
| a case | a unit below the placement line, `cases: {severity: critical, consecutive_checks: 1}` |

Three yearly readings are no trend, so `cpc` takes a one-day window and BOUNDEDNESS judges each year against that
year's lines alone. No strengths and no delays: no source gives one.

No decision is filed. A recorded hiring decision would be graded against a forecast that adds 2,000 trainees and
loses none, while the year lost 1,460: its no-action arm would come out *confirmed*, which reads as *hiring did
nothing*.

## The answers, written first

| | 2023 | 2024 | 2025 |
|---|---:|---:|---:|
| facilities below the placement line (critical) | 287 | 278 | 143 |
| below the target only (warning) | 20 | 32 | 86 |
| at or above the target | 6 | 3 | 84 |
| of the Inspector General's 26 critical facilities, below the line | 25 | 24 | 17 |
| the FAA | critical | critical | warning |

- **Walks.** Every facility's shortfall walks to the FAA. In 2023 hiring has no reading, so every walk is `open`;
  from 2024 hiring reads clean, the facility walks are `traced` with the FAA on the frontier, and the FAA's own walk
  is `unexplained`: its one declared cause did not fail.
- **Plan.** In 2023 adopting the staffing model would leave the FAA below the line (10,593 against a floor of
  10,678), so nothing beats doing nothing. **In 2024 the plan picks adopting the staffing model**: it lifts the FAA
  from critical to warning without moving a controller. Hiring adds trainees, which nothing judges, and never gains.
  In 2025 the target is already 12,563.
- **Cases.** 310 opened, 167 resolved, 143 open, 7 reopened. A case opens only on the finding the criterion names,
  one at or above `critical`.

## What the engine did

**The first run held every finding, walk, plan and gap, and departed on the cases**: 431 opened where the answers
say 310. The walk opened a case on every finding, below the model's case criterion as well, and the next check
closed each one again. The answers were right about the specification; the walk was fixed to match it -- a finding
below the criterion opens no case -- and **the second run held every field**: findings 849 of 849, walks 849 of
849, the plan 3 of 3, gaps 3 of 3, and the book 310 opened, 167 resolved, 143 open, 7 reopened. The plan's
objectives: 8,840 for every option in 2023; 8,670 for the staffing model against 8,690 for doing nothing or hiring
in 2024; 5,160 for every option in 2025.

## What each closed case says crossed

The case's own question needed an engine that could answer it, and from 0.2.39 it can. At each check of a case
the engine records the count and the lines it was judged against, keeps the pair the case opened on, and says of a
closed case what crossed: the count crossed the line when the closing count is above the line the case was last
found under; the line crossed the count when the count it was last found at is above the closing line; both when
each would have done it alone, or only the two together did. And a plan marks each option whose write reaches a
line.

**The answers came first.** `predict.py` applied that rule to the captures without the engine. Of the 167 cases
that close: **21 in 2024, every one by the count** -- no target moved that year -- and **146 in 2025: 6 by the
count, 95 by the line, 45 by both**. The plan, every year: `adopt_staffing_model` moves the FAA's two floors,
through its target; hiring moves none.

**The run held every one**: what each case says crossed, 310 of 310 (the 143 still open say nothing); the book's
counts, 27 by the count, 95 by the line, 45 by both; the plan's marks, 3 of 3 years.

**The FAA's own case closed by the line.** Last found below it in 2024, at 10,730 controllers under a placement floor of
12,438; closed in 2025 at 10,693 under a floor of 10,678. Its controllers fell by 37 and its line by 1,760.

**Two readings of the same 146.** Asked what moved at all: 3 whose count rose with the target unchanged, 84 where
both moved, 59 whose target fell with the count not rising. The engine asks what was enough. Of the 84 where both
moved, 45 needed both or had either, 36 would have closed on the falling line alone, and 3 on the rising count
alone; the 3 and the 59 read the same either way. So of the 146 cases that closed in 2025, 95 closed on the line
where the count alone would not have, 6 on the count where the line alone would not have, and 45 on both.

## On the released engine, from PyPI

`run_walks.py --engine published`, in a virtualenv holding `arbiter-engine` 0.2.39 from PyPI and nothing else of
the source, wrote the same `results.json` apart from each case's generated id and the time, and `score.py` held
every item: 849 findings and walks, 310 cases saying what crossed, 0 departures.

## What the case says, and what it does not

- **Detect.** Sound, at every facility, against lines the sources gave. The line is read off each facility, so a
  target that moves moves the judgement with it: the format working as declared, and the problem.
- **Explain.** Every facility's shortfall walks to the FAA, and the FAA's to hiring, which met its targets. The
  walk ends `unexplained` at the FAA: true of this model, which declares no cause beyond hiring. The sources name
  the rest -- retirements, the two-to-six-year pipeline, transfers out of critical facilities -- and none comes with
  a series this case holds.
- **Plan.** The plan recommends the move the FAA made. An objective that counts findings gains as much from
  lowering a line as from staffing a facility; the plan now marks the option whose write moves a line, and still
  ranks it the same.
- **Cases.** 95 cases closed in 2025 on the line alone, the FAA's own among them. A closed case now says so, where
  before it read exactly like a recovery.

## Running it

    python3 -m pip install 'arbiter-engine==0.2.39'
    python3 run_walks.py --engine published --out out
    python3 score.py --results out/results.json

`predict.py` writes `answers.json` again from the captures, without the engine. A case's id is generated each run;
everything else in `results.json` should match the copy here.
