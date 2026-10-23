# Nebraska's nursing homes and their nurse staffing, 2017-2026: a line withdrawn, homes retired

A case study for *Absent is not healthy*, appendix B. Every number in it is public, and every source is named. The
answers in `answers.json` were written by `predict.py` -- which applies the specification's rules to the captures
and never imports the engine -- before the engine ran; `score.py` holds a run to them.

The case: the 181 Nebraska nursing homes that reported in 2025, month by month from January 2017 to March 2026, as
CMS's Payroll Based Journal counts each day's residents and the hours their nurses and aides were paid to work. It
holds lines that move, lines that stand only for a while, and homes that leave.

## The situation, as the sources tell it

- **The line.** 42 CFR 483.35: licensed nurses around the clock, and an RN at least 8 consecutive hours a day,
  7 days a week. The HHS Inspector General (OEI-04-18-00450, August 2020) read a day as below the lines under 7.5 RN
  hours or 22.5 licensed nurse hours, a half-hour meal break out of each 8-hour shift.
- **The rating.** CMS, 6 April 2018 (QSO-18-17-NH): a home reporting 7 or more days in a quarter with no RN hours
  gets one star for staffing, from the ratings of July 2018; 5 March 2019 (QSO-19-08-NH): four days, from April
  2019, the line CMS's users' guide still draws.
- **The 2024 rule.** 10 May 2024 (Federal Register 2024-08273): 3.48 total nurse hours per resident day, 0.55 of
  them RN and 2.45 nurse aide, and an RN on site around the clock, phased in from 2026.
- **What undid it.** A federal court vacated its lines on 7 April 2025, and a second court in June; a law of 4 July
  2025 stayed them to 30 September 2034; CMS repealed them from 2 February 2026 (Federal Register 2025-21792). No
  home was ever bound by them.

## The model, in the format's own atoms

| Atom | Here |
|---|---|
| **Units** | the 181 homes, every Nebraska home that reported a day with residents and nurse hours in 2025; Nebraska's nursing home nurses and aides, as one unit; the national emergency over COVID-19 |
| **Links, with the cause end** | the workforce `staffs` every home; the emergency `strains` the workforce, as the 2024 rule has it. No strengths and no delays: no source gives one |
| **Readings** | per capture, for each home: the days its RN hours fell under 7.5 and the days its licensed nurse hours fell under 22.5; the quarter's days so far with no RN hours; the month's total, RN and nurse aide hours per resident day. The lines, on each home in the months they stood: the one-star days, 7 from July 2018 and 4 from April 2019; the 2024 rule's 3.48, 0.55 and 2.45 from May 2024 to March 2025. The emergency, `declared` or `not_declared`. The workforce, nothing |
| **Laws** | BOUNDEDNESS, upper: one day below a daily line is across it, and the one-star days at the line are. BOUNDEDNESS, lower: the 2024 lines. STABILITY on a state: a declared emergency is the bad state |
| **Levers** | none: no source says what the rating, the rule or its undoing did to a home's staffing |
| **Case** | a case opens at a warning and closes after three clean captures |

## The answers, written first

- **What the check finds.** The RN line holds the most homes in December 2017, 71, and the fewest in October 2025,
  19. The 2024 lines, from May 2024 to March 2025: 93 to 111 homes a month below at least one of the three, of 174
  to 180 read. A home with no day counted in a month holds no reading that month, and is unread.
- **The walk from a home** reaches the workforce at one hop and the emergency at two, through it. The workforce is
  never read, so every walk ends open on it; while the emergency was declared, March 2020 to March 2023, it stands
  at the frontier with the workforce open between it and the home.
- **The plan**: none. The model holds no lever, so the plan declines `no_candidates`.
- **The cases**: 2,069 opened, 1,376 of them reopenings.

## What the engine did, and what it could not do at first

**The first run held every answer** -- findings, walks, the named readings, plans, gaps, and all 2,069 cases by
the month they opened and closed -- **and its book held open what no check could close.** 232 cases on the 2024
rule's lines were open at the last capture, a year after the court struck the lines down. From April 2025 each
check on them found the home's hours and no line on the home, and the case book counted it as a check that could
not look, which restarts the count. The rule was written for a reading that falls silent; here the reading was
there every month, and it was the line that was gone.

**From 0.2.39, a withdrawn line closes its case.** A check that finds the reading and no line on the unit counts
toward closing as a clean one does, and a case that closes on one says the line was withdrawn. The answers were
written again first: **227 of the 232 close as withdrawn** -- 179 in June 2025, three checks after the vacatur; 27
in May and 19 in April, whose runs began with clean months before it; 2 in September, at a home whose silence had
restarted the count -- each saying the line it was last found against, and none after. 5 stay open, at two homes
that stopped reporting: silence still restarts the count. The run held every one.

**From 0.2.39, a unit can be retired.** The captures retire the three homes the federal provider file no longer
lists, each in the month after its last day with residents. A retired unit leaves the session and the graph with
its links, each case open on it resolves then and says so, and no later check or walk sees it; its readings stay.
The answers were written again first: **11 cases close as retired** -- the 5 the vacatur left open, and 6 more open
at the three homes when they left. The run held every one.

**The book, at the last capture**: 2,069 opened, 1,968 resolved -- 1,729 by the reading crossing back, 227 by a
withdrawn line, 11 by a retired unit, and 1 with no line to have crossed, the emergency's -- and 101 open.
None closed by a line moving: the one-star line moved once, from seven days to four, which made it stricter and
could close nothing.

## On the released engine, from PyPI

`run_walks.py --engine published`, in a virtualenv holding `arbiter-engine` 0.2.39 from PyPI and nothing else of
the source, wrote the same `results.json` apart from each case's generated id and the time, and `score.py` held
every item: 0 departures.

## What the answers concede

- **The homes that left before 2025 are not held**: the case reads the homes that stayed, and its early years are
  kinder than the state's.
- **A home missing from CMS's file is unread**, and each such month restarts the count of the home's open cases.
  The file does not say why a home is missing.
- **Unreported days are held apart**: a day with residents and no nurse hours of any kind is unreported, not below
  a line.
- **The director of nursing counts as the RN**, as the Inspector General and the one-star line count it.
- **The one-star line is held from the month it took effect**, read on the quarter so far, where CMS rates a whole
  quarter, later.
- **The cause the rule names is held and never read.** No series counts Nebraska's nursing home nurses and aides by
  month: every walk ends open on them.
- **A retirement is dated the month after a home's last residents**, not the day it closed, which the sources do
  not give.
- **No report names a home and a cause**, so nothing is confirmed.

## Running it

    python3 -m pip install 'arbiter-engine==0.2.39'
    python3 run_walks.py --engine published --out out
    python3 score.py out/results.json

`predict.py` writes `answers.json` again from the captures, without the engine. A case's id is generated each run;
everything else in `results.json` should match the copy here.
