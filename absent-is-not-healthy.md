---
title: "Absent is not healthy"
subtitle: "Checking what a BMC declares against what it reports"
author: "James Sheen · The Arbiter Project"
date: "Version 1.0, 2026-10-23 · DOI 10.5281/zenodo.23585862"
lang: en
header-includes: |
  ```{=typst}
  #show figure.where(kind: table): set block(breakable: true)
  ```
---

**Licence.** This text is licensed CC BY 4.0. The code and scripts that ship with it are Apache-2.0.

# Executive summary

A server's baseboard management controller reports its sensors, and a reader that waits for a reading to cross a line
learns nothing from a sensor that reports nothing: silence reads as health. This report checks what a board's
configuration declares against what its firmware reports -- on OpenBMC's public configuration corpus and on upstream
firmware -- and follows the result into the documents a factory hands a buyer.

**Three findings.**

1. **Absence has to be read right before it can be reported.** Across 362 configuration files, about three in ten
   declarations are not sensors at all, 1,260 declared rails carry no threshold to build them from, and 823 names are
   templates. Each makes a naive coverage check report a healthy board as broken, or a broken one as complete
   (section 3).
2. **On upstream firmware, a reader that waits for a crossing sees a healthy machine.** An emulated current board
   reports 28 of its 86 declared sensors, and a 2021 firmware image serves none through its modern interface at all;
   a reader that waits for a reading to cross a line sees nothing wrong in either. The released audit tool names the
   other 58 and does not call the board clean (section 4).
3. **Two declared limits contradict themselves and pass the schema.** Two boards' hot-swap controllers declare a
   threshold named *upper critical* as a low one, so as written each asserts whenever the part is at or below 105 °C or
   55 °C. Neither board is built upstream any more, so what they show is the shape the schema lets through, not a
   fault in use (section 3). Filed upstream as [`entity-manager` issue #38](https://github.com/openbmc/entity-manager/issues/38).

**The moved line.** A firmware update that moves a threshold looks exactly like a recovery unless the line is declared
and dated. The detection engine underneath (section 6) says how each closed case closed: on the reading, the line or
both, or because the line was withdrawn or the unit retired. Its evidence so far is public data, not hardware
(appendix B).

**What we ask.** One rack, on non-commercial terms, to run this against real hardware; upstream review of the filed
defect; and standards feedback, through OCP Hardware Management, on what an acceptance certificate should state on its
page (section 9).

# 1. The problem

A baseboard management controller (BMC) reads a server's sensors -- temperatures, voltages, fan speeds, power --
and reports them over Redfish to whatever watches the machine. A reader that waits for a reading to cross a line
learns nothing from a sensor that reports nothing. This report is about that silence, written for those who
build, buy and run servers at fleet scale, and about three ways a machine can be read as healthy when the true
answer is *not known*:

- **A sensor that does not report looks like one that sees nothing wrong.** Silence raises no alarm. A firmware
  image whose modern sensor collection is empty reports no sensor, no reading and so no alarm (section 4). A reader
  that builds its expectations from the wrong part of a board's declaration never expects the sensors it will not
  see (section 3). And a certificate held every absent sensor in its record and printed none of them, until it was
  fixed while this report was written (section 5).
- **A declared limit can contradict itself and pass the schema.** A board's configuration says where each sensor's
  limits sit, and nothing checks that a limit does what its name says: two upstream configurations name a threshold
  *upper critical* and declare it low (section 3).
- **A check that could not run can exit 0.** A tool that cannot say *I did not look* reports clean. The audit tool
  this report uses found that shape in itself, as its first issue, and closed it before its first release.

Each is a question of what the reader of a result can tell apart, and the method is built to keep them apart. The
three findings on page one are the first two shapes: findings 1 and 2 the first, on the corpus and on firmware, and
finding 3 the second. The third shape is a rule of the method (section 2), and it is the certificate's own check,
which passed a page that lacked what its record held (section 5).

# 2. Method

Five rules, each one at work in the sections that follow.

- **The declaration is the specification.** A board's configuration says which sensors it has and where their
  limits sit, and the running machine is checked against it, never the other way about: what the machine reports
  is compared with what was declared, and the difference is the finding (sections 3 and 4).
- **Presence is three-valued.** A sensor is present and reading, present but disabled or unreadable, or entirely
  absent: three conditions with three responses, and the middle one is the case the audit tool exists for. A
  declaration's kind is three-valued for the same reason -- a sensor, not a sensor, or of a type the reader does
  not recognise -- and an unrecognised type is reported by name, never judged absent (section 3).
- **Every result says what it did not do.** Beside what was found: how many checks were tried, which were declined
  and why, and what the model never declared at all, so that *clean* means checked and held, not unchecked
  (sections 5 and 6).
- **An incomplete walk withholds its absence findings.** A walk that could not complete is not a board with
  missing sensors. On the released tool's own mock, one board read three ways: whole, it passes; with one sensor
  gone, that sensor is named absent and the run exits 1; with its sensor collection failing, the walk is reported
  incomplete, no sensor is called absent, and the run exits 2, *could not complete*.
- **Answers are written before runs.** Where this report runs a case, a predictor that applies the specification
  without the engine writes the answers first, and the run is held to them (appendix B).

Every count is measured at a revision the report names and reproduced from released versions (section 8). Every
tool this report runs is the project's own, released on PyPI; the corpus, the firmware, the emulator and the public
data are not.

# 3. Findings on the public corpus

OpenBMC's `entity-manager` holds the configuration files that declare, board by board, which sensors a machine
has and where each one's limits sit. Every count in this section is measured at its revision `495e0a4`
(committed 15 October 2026), across 362 configuration files, and every one is the count the released
`bmc-sensor-audit` 0.3.19 prints with its `census` command, which reads the corpus as the tool reads a board.
Appendix A tables every count at both revisions.

## What a reader must get right before it can say *absent*

A coverage check compares what a board's configuration declares with what the machine reports, and calls the
difference absent. Read naively, the declarations make that check wrong in both directions. It reports a healthy
board as missing sensors, which teaches its users to ignore it; or it reports a board as complete because it
never built the expectation that would have failed, and nothing downstream can notice an expectation that was
never built. Five shapes of the corpus produce one or the other, and the format's documented example prepares a
reader for none of them.

- **Not every declaration is a sensor.** 3,268 of the 10,971 declarations, about three in ten, are things the
  configuration declares exactly as it declares sensors and that can never appear in a Redfish `Sensors`
  collection: GPIO leak detectors and device-detect lines, PID control loops and stepwise fan curves, EEPROMs
  among them, 83 types in all. Expected as sensors, every one of them is missing on a healthy board. A further
  107, of 17 types the reader does not know, are reported as unrecognised and never as absent: a type a tool
  cannot classify is a question for a person, not a regression.
- **One entry can declare many sensors.** The documented example declares one sensor per entry. 1,310 entries
  instead declare a set of rails in a `Labels` array -- up to 33 in one entry, 5,891 in all -- and 1,260 of
  those rails carry no threshold. A reader that takes an entry's rails from its thresholds never constructs
  those 1,260: nothing expects them, so their absence can never be reported.
- **Names are templates.** 823 declared names, about one in thirteen, carry a template such as `$bus` or
  `$index`, substituted when the device is found. Compared literally, every one of them is missing on a healthy
  board. The format's documentation lists three template strings; the code substitutes any property of the
  matched device, and the names use five.
- **A file can hold several records, and some files are not strict JSON.** The documentation describes a file
  as one JSON object; 78 of the 362 hold an array of records. Twelve carry C-style comments, which the format
  allows and a strict JSON parser refuses. A reader that skips a file it cannot parse reports that file's sensors
  as *undeclared* rather than *unread*: a clean bill of health for every board the file describes.
- **A threshold's name is free text; its `Direction` decides.** The 16,383 thresholds spell their names fifteen
  ways -- among them `upper critical`, `higher critical`, `HardShutdown`, `Warning`, and `lower non-recoverable`
  beside `lower non recoverable` -- where the documented example shows four. The schema requires `Direction` and
  allows it two values, while `Name` may be any string, so it is `Direction` that says which side a threshold
  guards: 10,232 are `greater than` and 6,151 `less than`.

## Two thresholds contradict themselves

On the Yosemite V2 and Yosemite V3P5 baseboards, the hot-swap controller's `temp1` threshold is named
`upper critical` and declared `Direction: less than`. The sensor daemon never reads the name, so as written each
is a critical *low* threshold, at 105 °C and 55 °C: one that asserts whenever the part is at or below that
temperature. Across the 362 files and their 16,383 thresholds, these are the only two whose name contradicts
their direction. Both are valid against the schema, which constrains each field of a threshold on its own and
relates none to another. Neither board is built upstream any more: on 16 May 2025 `openbmc/openbmc` removed both
machine layers, Yosemite V2's `meta-yosemitev2` and Yosemite V3.5's `meta-greatlakes` (renamed from `fby35` in
2022), and the two configurations stayed. What they show is the shape the schema lets through, not a fault on a
board upstream still builds. Filed upstream as [`entity-manager` issue #38](https://github.com/openbmc/entity-manager/issues/38).

## Counts drift; shapes do not

Nine weeks earlier, at revision `0ada048` (committed 14 August 2026), the same `census` counted 349 files, 9,424
declarations, 2,069 of them not sensors, and 15,860 thresholds, with the same two contradictions. The counts in
this section are true of `495e0a4` and will move at the next revision; the shapes held at both. So `census` names
the commit it counted, and whether any file under the directory differs from it: anyone can take the counts again, at
this revision or the next.

# 4. End to end on upstream firmware, reproducible

Section 3 is about what boards declare. This section runs the check end to end: upstream firmware, booted under
the QEMU emulator, walked over Redfish and compared with its own board's declarations. Both recordings are of
firmware this project did not write, and both ship with the released `bmc-sensor-audit` 0.3.19, so everything
here reproduces from a clone of that release, with no hardware.

## A current board, under emulation

The bletchley board's upstream image, built by OpenBMC's continuous integration on 15 August 2026 and booted
under QEMU 10.2.1, serves its sensors through `bmcweb`, OpenBMC's Redfish server. An emulator has no
manufacturing data, so the board appeared only after a synthetic FRU record was written into its EEPROM. Walked
on 18 August 2026, the machine reported 28 sensors on 3 chassis, all in the modern `Sensors` tree, all reading.

Compared with the board's three upstream configuration files, the released tool counts 86 declared sensors: 28
matched and reading, 58 declared and not reported at all, and none reported that nothing declares; six more
declarations it classifies out as fan-control loops and curves. It exits 1, regressions present. It does not
report a clean board.

Two things in that result matter beyond this board. Every one of the 28 matches needed a normalised name: the
configuration declares `IMON_FAN0` and the machine reports `IMON FAN0`. Compared exactly, all 86 would read as
missing and all 28 present sensors as undeclared; the tool pairs them, and says of each pairing that it was not
exact, for a person to confirm. And the 58 absences are, one for one, devices the emulated board does not have:
the rails of its hot-swap controllers and current monitors (46), its fans' tachometers (8), and its front panel's
humidity and temperature sensor, declared twice, once for each of two parts (4). QEMU's model of this board puts
only temperature sensors, GPIO expanders, EEPROMs and a clock on its I2C buses, and its model of the board's
system-on-chip has no device behind the fan controller. On a physical board the same 58 names are the list to
check: each one is reporting, or is missing for a reason someone should know.

## The mirror: firmware from 2021

The witherspoon board's OpenBMC 2.9.0 release image, published in 2021 and booted under the same emulator, is
the same trap facing the other way. Its modern `Sensors` collection is empty. Its older `Thermal` document
carries two temperatures, each with a reading and thresholds, and four fans, each with a reading; its `Power`
document carries a power-control entry and no reading. A reader that knows only the modern collection walks this
machine and finds nothing: no sensor, no reading, and so no alarm -- and nothing in the walk tells it that this
silence is not health.

A current image can be the same case for the opposite reader. `bmcweb` still carries the handlers for the older
`Thermal` and `Power` documents, but behind a build option that is off by default and whose own description says
it "will be removed June 2026"; at `bmcweb` revision `7da5af6` it is still there and still off. A monitoring integration written against the older documents finds them missing on such an image, and absent
again reads as nothing to report. The released tool reads both shapes.

## What emulation can and cannot show

It can show that the check runs end to end on firmware nobody wrote for it; that it names every declared sensor
a machine does not report, rather than passing over it; and that it does not call a board clean while any of
them is missing. It cannot show what a physical board reports. The emulator models a subset of each board's
devices, so the population is partial by construction and its absences are facts about the emulator; it has no
manufacturing data, so a FRU record had to be written by hand; and the older `Power` path has still never
carried a real reading here. A capture from physical hardware is the next evidence this needs (section 9).

# 5. From factory to fleet

Sections 3 and 4 judge one board against its declaration, once. This section follows that judgment into the
documents a factory hands a buyer, and out across the buyer's fleet. Each link is its own released tool --
`bmc-sensor-audit` 0.3.19 for the capture and the attestation, `odm-cert-generator` 0.2.6 for the certificate,
`fleet-sensor-baseline` 0.2.3 for the fleet -- and each link's job is to keep in view what the one before it did
not establish. The first two ran here on the bletchley capture of section 4, as a factory station would run them.

## The capture, and why the parse is the redaction

A Redfish walk of a real machine returns serial numbers and asset tags, so `capture` writes only the parsed sensor
set, never the raw payloads, and a capture can travel with the documents built on it. It also has a content
handle, a SHA-256 over its bytes, which is how a certificate later says which capture it was judged from.

## The attestation: what was checked, what was declined, and the numbers

The attestation records, for one run, what was checked, what was declined, and the measurement behind every
finding. Its format refuses a file in which any finding lacks its measurement, and requires its lists of what was
left out to be present even when empty, since a missing list would read as *nothing was left out*. Checking one
needs no engine and no hardware.

On the bletchley capture it records 56 checks over the 28 sensors that reported: 26 findings, 28 declined, and two
that held. The 26 are each a reading past a declared limit -- `P12V_AUX` reads 14.8985 against an upper critical
limit of 12.61 -- and they are the emulator's readings, not a board's health (section 4). The 28 declined are each
sensor's stability, for *too few observations to detect oscillation*, since one walk cannot show a sensor
oscillating; the attestation says so rather than passing them. The two that held are `P12V_FAN0` and `P12V_FAN2`,
each reading inside its declared limits.

What it cannot carry is absence. It counts what reached the check, 28 sensors, and nothing on it says 28 of 86. Nor
is it signed: it establishes nothing about tampering, and it carries the detection engine's own statement of what
its evidence establishes, verbatim.

## The certificate, and the page a person reads

A certificate has the opposite job to the audit's: it names the unit -- serial, work order, station, signer --
and the audit tool holds none of them. It never claims a flat pass. It prints the denominator, and a section
headed *Not part of this judgment* that is emitted even when every list in it is empty. Given the declaration
diff, it states declared against present and names each absent sensor; without one, it says on the page that it
cannot. It records the capture it was judged from by handle, and whether it computed that handle or was only
handed it. A certificate for a unit with findings is still written, and exits 1. And `verify` holds the PDF to the
JSON record behind it in both directions: no number on the page that the record lacks, and nothing the record must
show missing from the pages.

On the bletchley capture the record holds all of it: 56 checks over 28 sensors -- 26 findings, 28 declined, two
held -- 86 declared and 58 absent, each named, and the capture's handle, computed and matching. **On 0.2.5 the page
did not -- found writing this section, and fixed in 0.2.6, released on 16 October 2026.** A certificate was then one page
by design, with page breaks turned off so that one which overflowed would be seen
to. With 26 findings, the renderer drew everything after the first two of their measurements below the page's
bottom edge: the section *Not part of this judgment* -- which opens, *"A certificate that shows only what was
checked reads as a clean bill of health for every question nobody asked."* -- the 58 absent sensors, and the
capture's handle. On paper the certificate listed 26 findings and said nothing of an absence. `verify` passed,
because it asked only whether every number on the page was in the record, never whether the record had reached the
page. On 0.2.6 the same certificate runs to five pages, each naming the unit and saying which page of five it is; page one states 58 of the 86 declared sensors
absent beside the scope; every section and the capture's handle are printed; and `verify` passes it only because
everything the record must show is on a page.

## What an acceptance certificate should state, and what it does not attest

It should state, on the page a person reads and not only in the record behind it:

- the denominator: how many checks, over how many sensors;
- declared against present, naming every declared sensor that did not report;
- what was not judged, each with its reason;
- the measurement behind each finding;
- which capture it was judged from, by content, and whether that was checked.

It does not attest that the document is genuine, since nothing in it is signed; that the machine was audited
again, since its authority is the attestation's; that the declaration it was judged against is right, since a
contradiction in the declaration, like the two in section 3, is the expectation it judges by; that conformance or
fault-injection tests ran, which is a separate verdict; or anything about time, since one capture judges one moment.

## Across a fleet

`fleet-sensor-baseline` reads the buyer's own captures and answers the two questions one machine cannot: what
changed on this unit across time, and which units differ from their cohort. Its own example: *"A tray reported
forty-five sensors before a firmware update and forty-two after it. Every remaining sensor is healthy."* An audit of
that tray alone finds nothing, because the machine agrees with itself; only its previous capture disagrees. Across
time, `drift` reads what changed in the records -- firmware, the sensor set, which units reported -- and `compare`
hands two stored captures of one unit to the audit tool's own regression check, the threshold audit across time.
Across the cohort, a baseline is derived from the fleet and the units that differ from it are named.

Two absences need care at fleet scale. A baseline derived from a fleet cannot see an absence the whole cohort
shares: two thousand trays that lost the same sensor in the same firmware agree with each other perfectly. So
every derived baseline carries that sentence as part of its format, and a manufacturer's declaration, where one
exists, wins. And a majority rule inverts at rack scale: on 24 trays where 2 had lost a sensor, an earlier version
dropped the sensor from the baseline and reported the 22 healthy trays instead. Now a sensor the cohort disagrees
about is reported once, against the cohort, naming the units that lack it, and a unit that could not be walked is
always reported as such. None of this has yet run on a real fleet (section 7).

# 6. The engine underneath, and the moved line

The attestation in section 5 is the work of a detection engine, `arbiter-engine`, which the audit tool runs
beneath its `detect` command and which is released on PyPI on its own; this report uses version 0.2.39. Its
description of itself is one line: *"A detection engine that reports what it did not check."*

## Declared invariants, and an output that keeps what it did not check

A domain model, written in YAML, declares what a system is made of -- its kinds of unit, the readings each one
carries, and the links between units -- and which of eight axioms each reading must satisfy: `BOUNDEDNESS`,
`STABILITY`, `HOMEOSTASIS`, `MONOTONICITY`, `CONSERVATION`, `CONNECTIVITY`, `CONSISTENCY` and `RESPONSIVENESS`.
The engine holds the system as a graph of those typed units and links, judges each reading against its axioms, and
from a finding walks the graph toward what could explain it. Each subject in this report -- a board, a country's
air traffic control facilities, a state's nursing homes -- is a model, not code.

Every pass returns what it found; what it did not check, each with a reason from a closed vocabulary of fourteen;
how many checks it tried; and questions, for what the model never declared at all. So a clean result means that
invariants were tested and held, and it is told apart from nothing having been testable. The bletchley
attestation is this output: its 56 checks are two axioms, `BOUNDEDNESS` and `STABILITY`, over 28 sensors; its 28
declines share one reason, `insufficient_samples`; and the statement it carries about its own evidence is the
engine's.

## A resolved case says what crossed

A finding at the severity a model names opens a case, and the case closes after the clean checks the model names.
Until 0.2.39 a closed case said only that it had closed: a reading that crossed back over its line, and a line that
moved past its reading, closed a case the same way. From 0.2.39 a closed case says what crossed -- the reading, the
line, or both -- with the readings and lines it compared. A case on a line the unit no longer carries closes as
withdrawn. A unit can be retired: it leaves the graph, and each case open on it closes saying so. The case book
counts each kind.

**For hardware this is the point.** A board's thresholds are declared in its configuration, and a firmware update
can change them: the audit tool's firmware regression gate exists to ask which sensors an update removed, renamed
or re-thresholded. A case that closes because a threshold moved, and not because the part recovered, reads
exactly like a recovery, unless the line is declared, dated and compared.

## The evidence, in appendix B

Two cases from public data, each with its answers written first by a predictor that never imports the engine, and
each reproduced on 0.2.39 as installed from PyPI with no departure from them.

- **Air traffic controllers: a line that moved.** Between its plan for 2025-2028, with staffing as of September
  2024, and its plan for 2026-2028, with staffing as of September 2025, the FAA lowered its staffing target from
  14,633 controllers to 12,563, and 275 of its 313 facilities' targets with it. Of the 146 cases that closed on the
  staffing of September 2025, 95 closed on the line where the count alone would not have, 6 on the count where the line alone
  would not have, and 45 on both. The FAA's own case closed with 37 fewer controllers, because its line fell by
  1,760.
- **Nebraska's nursing homes: a line withdrawn, homes retired.** Of the 1,968 cases the book closed, 1,729 closed
  on a reading crossing back; 227 as withdrawn, on the lines of a 2024 federal staffing rule after a court struck
  them down; 11 as retired, at three homes the federal provider file stopped listing; and one with no line to
  cross.

Neither is hardware, and section 7 says so: the moved line has no hardware exhibit yet.

# 7. Limits

- **No real fleet data yet.** The fleet tool's behaviour is cited from its documentation, not shown on a fleet.
- **Two boards, one emulator.** The end-to-end evidence is a current board and a 2021 image under QEMU. An absence
  under emulation is a fact about the emulator, not a defect in the firmware, and no physical board has been
  captured.
- **The two contradictions have not been observed on hardware**, and no upstream image could show them: neither
  board is built upstream any more. Their consequence is read from the consumer's source.
- **What counts as a sensor is the released reader's classification**, derived from the corpus; the 107
  declarations of types it does not recognise are reported, not judged.
- **The attestation and the certificate are not signed.** They establish nothing about tampering.
- **Every count is pinned to a revision**, and moves with the next one.
- **The moved line's evidence is public-sector data**; its hardware application has no exhibit yet.
- **Every tool in the chain is this project's own**; the corpus, the firmware, the emulator and the public data are
  not. Writing this report found a defect in one of those tools, the certificate's page, and its fix was released
  before the report cites it (section 5).

# 8. Reproducibility

Everything the report states reproduces from released versions and named revisions.

**What it runs, from PyPI.** `bmc-sensor-audit` 0.3.19, with its `detect` extra and its `census` command; `arbiter-engine` 0.2.39 beneath it;
`odm-cert-generator` 0.2.6, and 0.2.5 for the page it fixed; and `presence-audit` 0.2.6, the library the audit tool
and the certificate generator share, which defines the attestation format. Each check installs exactly these into an environment of its own. `fleet-sensor-baseline`
0.2.3 is cited from its documentation and not run.

**What it reads, at named revisions.** `entity-manager` at `495e0a4`, and at `0ada048` for the counts of nine weeks
earlier; `dbus-sensors` at `1ae7e41`; `bmcweb` at `7da5af6`; QEMU at `v10.2.1`. The two firmware recordings, and the
configurations of the board the first is compared against, are vendored in `bmc-sensor-audit` at `v0.3.19`, each
recording carrying its provenance and the configurations carrying upstream's licence beside them.

**How each figure is checked.** Every figure in the text has a row in the claims ledger that ships with the report:
the source it rests on, and a command that checks it, or a file and the text it must hold. The commands fetch each
upstream source at its revision and install each tool at its version, so a figure is checked against the thing it
describes and never against a note about it. Appendix B's two cases run with `arbiter-engine` 0.2.39 from PyPI, and
each scorer holds its run to the answers written before it and fails on any departure.

**What is recorded rather than rerun.** Booting the two images under the emulator and walking them was done once;
the recordings are replayed, not recaptured, and their provenance says how they were made.

**Licences.** The text is CC BY 4.0, and the code and scripts that ship with it are Apache-2.0. The five tools in the
chain are on PyPI under Apache-2.0. Appendix B's data
are public records of United States government agencies, each source named in its case's story.

# 9. What we ask

- **One rack**, on non-commercial terms, to run this chain against real hardware: the coverage check on physical
  boards, a buyer's captures across time and firmware, and a certificate for a unit that was really built. Each is
  an exhibit section 7 says this report lacks.
- **Upstream review** of the two contradictory thresholds and of the checks that found them, filed as
  [`entity-manager` issue #38](https://github.com/openbmc/entity-manager/issues/38).
- **Standards feedback**, through OCP Hardware Management: on what an acceptance certificate should state on its page
  (section 5), and on reporting absence as a result of its own rather than as silence.

# Appendix A. The corpus tables

Counted by the released `bmc-sensor-audit` 0.3.19's `census`, at the two revisions of `entity-manager` section 3
names. Every figure here has its row in the ledger.

**Table A.1. The corpus at two revisions, each dated by its commit.**

| | `0ada048`, 14 August 2026 | `495e0a4`, 15 October 2026 |
|:---|---:|---:|
| Configuration files | 349 | 362 |
| not strict JSON (C-style comments) | 10 | 12 |
| holding an array of records | 76 | 78 |
| Declarations, as the released reader reads them | 9,424 | 10,971 |
| not sensors | 2,069 | 3,268 |
| of how many types | 82 | 83 |
| of types the reader does not recognise | 107 | 107 |
| of how many types | 17 | 17 |
| with a runtime template in the name | 820 | 823 |
| disabled in the configuration | 106 | 106 |
| Entries declaring rails in a `Labels` array | 1,233 | 1,310 |
| the most rails in one entry | 33 | 33 |
| Rails declared | 5,617 | 5,891 |
| rails no threshold names | 1,238 | 1,260 |
| Thresholds | 15,860 | 16,383 |
| spellings of their name | 15 | 15 |
| with `Direction: greater than` | 9,891 | 10,232 |
| with `Direction: less than` | 5,969 | 6,151 |
| whose name contradicts their direction | 2 | 2 |

**Table A.2. Threshold names, as written, at `495e0a4`.** `Direction` takes its two values throughout; the
name is free text.

| Name, as written | Thresholds |
|:---|---:|
| `upper critical` | 6,269 |
| `lower critical` | 3,880 |
| `upper non critical` | 2,328 |
| `upper non recoverable` | 1,596 |
| `lower non critical` | 1,512 |
| `lower non recoverable` | 742 |
| `Ambient Lower Critical` | 12 |
| `Ambient Upper Critical` | 12 |
| `higher critical` | 8 |
| `higher non critical` | 8 |
| `HardShutdown` | 5 |
| `SoftShutdown` | 4 |
| `Warning` | 4 |
| `lower hardshutdown` | 2 |
| `lower non-recoverable` | 1 |

```{=typst}
#pagebreak(weak: true)
```

**Table A.3. Declared as sensors are, and not sensors, at `495e0a4`:** the ten largest of 83 types.

| `Type` | Declarations |
|:---|---:|
| `GPIOLeakDetector` | 738 |
| `GPIODeviceDetect` | 686 |
| `Pid` | 346 |
| `Stepwise` | 306 |
| `EEPROM` | 202 |
| `IntelFanConnector` | 117 |
| `DeltaECD27010006CapacitorBankUnit` | 60 |
| `Pid.Zone` | 49 |
| `Artesyn7000552480000PowerSupplyUnit` | 48 |
| `DeltaBBUBU123AE000BatteryBackupUnit` | 48 |
| 73 more types | 668 |
| **All 83 types** | **3,268** |

**Table A.4. Of types the released reader does not recognise, at `495e0a4`:** each reported by name, never
judged absent.

| `Type` | Declarations |
|:---|---:|
| `LM25066` | 36 |
| `ISL69269` | 20 |
| `HPEFan` | 14 |
| `ChassisIntrusionSensor` | 8 |
| `TMP464` | 5 |
| `ADT7461` | 4 |
| `CRPS185` | 4 |
| `Intel HSBP CPLD` | 3 |
| `CFMSensor` | 2 |
| `ExternalSensor` | 2 |
| `UCD90160` | 2 |
| `UCD90320` | 2 |
| `HostCpuUtilization` | 1 |
| `IntelHsbpTempSensor` | 1 |
| `IpmbPowerMonitor` | 1 |
| `NMSensor` | 1 |
| `Sum` | 1 |
| **All 17 types** | **107** |

# Appendix B. The case studies: the moved line's evidence

Two cases from public data ship beside the report, in its repository's `appendix-b/`, as files a reader runs: each
case's model, the captures of its public sources, the predictor that wrote its answers before the engine ran, the
answers, the runner, the scorer -- which holds a run to the answers and fails on any departure -- the reference
results, and the story, which names every source. With only the released engine installed, from `appendix-b/`:

    python3 -m pip install 'arbiter-engine==0.2.39'
    cd faa
    python3 run_walks.py --out out
    python3 score.py --results out/results.json
    cd ../nursing_homes
    python3 run_walks.py --out out
    python3 score.py out/results.json

On 0.2.39 from PyPI both write their reference results again, apart from each case's generated identifiers and the
time, with no departure.

## B.1 Air traffic controllers, 2023 to 2025: a line that moved

*Can the engine tell a moved line from a mended unit?* The captures are three editions of the FAA's controller
workforce plan -- the plan to Congress for 2024-2033, and the plans for 2025-2028 and 2026-2028 -- with staffing as of
September 2023, 2024 and 2025. Each of 313 facilities is a unit with two floors read off it: its
staffing target, and 85 percent of it, the line the FAA and its controllers' union set to prioritise placement. A
case opens on a facility below that second line.

| The book | Opened | Resolved | Open | Reopened |
|:---|---:|---:|---:|---:|
| all three years | 310 | 167 | 143 | 7 |

| Closed | By the count | By the line | By both |
|:---|---:|---:|---:|
| on September 2024's staffing | 21 | 0 | 0 |
| on September 2025's staffing | 6 | 95 | 45 |

The FAA's own case closed on September 2025's staffing, by the line: last found at 10,730 controllers under a floor of 12,438, it closed at
10,693 under a floor of 10,678.

The case's first run departed from its answers on the cases: 431 opened where the answers say 310, because the walk
opened a case on every finding, below the model's case criterion as well. The walk was fixed to the specification, and
the second run held every field.

## B.2 Nebraska's nursing homes, 2017 to 2026: a line withdrawn, homes retired

The captures are 111 months of CMS's Payroll Based Journal, January 2017 to March 2026, for the 181 Nebraska homes
that reported in 2025, with each month's federal lines on each home: the daily nurse lines, CMS's one-star line, and,
from May 2024 to March 2025, the lines of a 2024 staffing rule that a federal court vacated in April 2025, a law
stayed in July 2025, and CMS repealed from February 2026.

| The book | Opened | Resolved | Open |
|:---|---:|---:|---:|
| all 111 months | 2,069 | 1,968 | 101 |

| Resolved | By the reading | Line withdrawn | Unit retired | With no line |
|:---|---:|---:|---:|---:|
| all 111 months | 1,729 | 227 | 11 | 1 |

Before 0.2.39 the cases on the 2024 rule's lines stayed open after the court struck the lines down: each check found
the home's hours and no line, and counted as a check that could not look. From 0.2.39 a line that is gone closes its
case as withdrawn, and the three homes the federal provider file stopped listing are retired.

# Appendix C. The attestation format

The audit tool's record of one run, `presence-audit/attestation/2`, as its own document at `bmc-sensor-audit`
`v0.3.19` defines it: what was checked, what was declined, and the measurement behind every finding. `detect
--attest-out` writes it, from 0.3.7 at `/2`, and `validate-attestation` checks it with no engine and no hardware --
and still reads `/1`. Within one id the format may gain keys and never change what one means; a change of meaning is
a new id.

| Key | What it holds |
|:---|:---|
| `format` | the contract the file claims |
| `target` | what was audited: a Redfish URL, or the path of a recorded walk. It may name an internal host, which `--attest-target-label` replaces with a neutral name |
| `engine.schema_version` | the envelope contract the judgment was made under -- not the engine's release number |
| `engine.boundary` | the engine's own statement of what its evidence does and does not establish, quoted verbatim |
| `checked` | the denominator: how many questions, over how many things |
| `findings` | what went wrong, each named on the board, with its axiom, severity and statement |
| `not_checked` | what could not be evaluated, and why |
| `evidence` | one per finding: the reading, the threshold it crossed and on which side |
| `unattested` | problem types the engine declined to attest, each with its reason |
| `unread_feeds` | observations that were fed and that nothing in the model read |

**Three invariants**, which `validate-attestation` enforces. Every finding carries its measurement, so the evidence
and the findings are equal in number. The record names the envelope contract its judgment was made under. And the two
lists of what was left out, `unattested` and `unread_feeds`, are present even when empty, because a missing list
would read as *nothing was left out*.

**What validation does not check, on purpose:** that there are findings. A genuinely clean board produces an
attestation with none, and it is valid.

**What it is not:** signed. Nothing in it establishes provenance against tampering, and the engine says so itself, in
the boundary it stamps on every entry of evidence.

# Appendix D. Glossary

**Absent.** Declared, and not reported by the machine at all; distinct from present but disabled or unreadable
(section 2).

**Attestation.** The audit tool's record of one run: what was checked, what was declined, and the measurement behind
every finding (appendix C).

**Axiom.** One of the eight kinds of invariant a reading can be declared to satisfy, from `BOUNDEDNESS` to
`RESPONSIVENESS` (section 6).

**Baseline, cohort.** Units of one kind compared with each other; a baseline is derived from them, and cannot see an
absence they all share (section 5).

**BMC.** Baseboard management controller: it reads a server's sensors and reports them, here over Redfish.

**Capture, walk.** One reading of a machine's Redfish sensor documents, kept as the parsed sensor set; a walk is
complete when every part of it was read (sections 2 and 5).

**Case.** One problem, from the finding that opened it to the clean checks that closed it. A closed case says how it
closed: on the reading, the line or both, or because the line was withdrawn or the unit retired (section 6).

**Certificate.** The document that names a unit and states what its attestation established and did not (section 5).

**Configuration, declaration.** A board's `entity-manager` file: which sensors it has, and where their limits sit
(section 3).

**Coverage check.** The comparison of what a board declares with what the machine reports (sections 3 and 4).

**Decline.** A check that was not run, with its reason from a closed vocabulary (section 6).

**Denominator.** How many checks a pass tried; findings and declines do not add up to it (sections 5 and 6).

**`Direction`.** The field that says which side of a threshold is the bad one, `greater than` or `less than`
(section 3).

**Handle.** A SHA-256 over a capture's bytes, which binds a document to the capture it was judged from (section 5).

**Line.** A declared limit a reading is judged against: a threshold, a target, the floor of a rule. A moved line is a
limit that changed (section 6).

**Matched inexactly.** A declared sensor paired with a reported one by a normalised name, and flagged for a person to
confirm (section 4).

**Not a sensor; unrecognised.** The reader's classification of a declaration that can never report a reading, and of
one whose type it does not know (section 3).

**Rail.** One of several sensors that a single `Exposes` entry declares, through its `Labels` array (section 3).

**Template name.** A declared name with a substitution made when the device is found, such as `$bus` (section 3).

**Withdrawn, retired.** How a case closes when its line is taken off the unit, or when the unit itself leaves the
system (section 6).
