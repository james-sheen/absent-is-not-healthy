# Appendix B: the case studies behind the moved line

The two public-data case studies that *Absent is not healthy* cites in section 6 and appendix B, as files a reader
runs: each case's model, its captures, the predictor that wrote its answers before the engine ran, the answers,
the runner, the scorer, the reference results and the story.

| Case | What it shows | Story |
|---|---|---|
| `faa/` | the FAA's air traffic controller staffing against its own targets, 2023-2025: **a line that moved** | `faa/STORY.md` |
| `nursing_homes/` | Nebraska's nursing home nurse staffing against federal lines, 2017-2026: **a line withdrawn, and homes retired** | `nursing_homes/STORY.md` |

## Running them

On Python 3.10 or later, with only the released engine installed:

    python3 -m pip install 'arbiter-engine==0.2.39'
    cd faa && python3 run_walks.py --out out && python3 score.py --results out/results.json
    cd ../nursing_homes && python3 run_walks.py --out out && python3 score.py out/results.json

`run_walks.py` feeds the captures to the engine in-process, and after each one runs the walk -- `walks.py`, which
checks, opens cases, ranks causes, plans, and lists what the declaration cannot explain, calling only the engine's
own verbs. `score.py` holds a run to `answers.json` and prints every place it departs. `predict.py` writes
`answers.json` again from the captures alone, without the engine. A case's id is generated each run; everything
else in `results.json` should match the copy here. On the two machines measured, the air traffic controllers case
ran in two to four minutes and the nursing homes in three to sixteen.

## Licences and sources

The code here is Apache-2.0 (`LICENSE`). The data are United States government works: the FAA's controller
workforce plans and the DOT Inspector General's report, CMS's Payroll Based Journal and provider files, the
Federal Register and the Code of Federal Regulations, each named where its figures are used. The stories are part
of the report, and licensed with it, CC BY 4.0.

`MANIFEST.sha256` lists every file with its SHA-256, as staged.
