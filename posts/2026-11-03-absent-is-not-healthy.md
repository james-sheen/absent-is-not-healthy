# Absent is not healthy

*What OpenBMC's configuration corpus declares, and what upstream firmware reports.*

---

A baseboard management controller reads a server's sensors and reports them over Redfish. A reader that waits for a reading to cross a line learns nothing from a sensor that reports nothing, so silence reads as health. On OpenBMC, what *should* be there is written down: `entity-manager` holds the configuration that declares, board by board, which sensors a machine has and where each one's limits sit. Compare what a board declares with what its machine reports, and the difference is the finding: declared, and absent.

That comparison looks like a set difference. It is not one, and the reasons are in the corpus itself. This post is an excerpt of a technical report, *Absent is not healthy*, whose every figure has a row in a claims ledger that checks it against upstream at the revision named.

## Five shapes the documented example does not prepare a reader for

Every count in this section is measured at `entity-manager` revision `495e0a4` (committed 15 October 2026), across 362 configuration files, with the declarations read as the released `bmc-sensor-audit` reads them.

**Not every declaration is a sensor.** 3,268 of the 10,971 declarations, about three in ten, are things the configuration declares exactly as it declares sensors and that can never appear in a Redfish `Sensors` collection: GPIO leak detectors and device-detect lines, PID control loops and stepwise fan curves, EEPROMs among them, 83 types in all. Expected as sensors, every one of them reads as missing on a healthy board. A further 107, of 17 types the reader does not recognise, are reported as unrecognised and never as absent: a type a tool cannot classify is a question for a person, not a regression.

**One entry can declare many sensors.** The format's documented example declares one sensor per entry. 1,310 entries instead declare a set of rails in a `Labels` array – up to 33 in one entry, 5,891 in all – and 1,260 of those rails carry no threshold. A reader that takes an entry's rails from its thresholds never constructs those 1,260: nothing expects them, so their absence can never be reported.

**Names are templates.** 823 declared names carry a template such as `$bus` or `$index`, substituted when the device is found. Compared literally, every one of them is missing on a healthy board. The format's documentation lists three template strings; the code substitutes any property of the matched device, and the names use five.

**A file can hold several records, and some files are not strict JSON.** 78 of the 362 files hold an array of records where the documentation describes one object, and 12 carry C-style comments, which `entity-manager` accepts and a strict JSON parser refuses. A reader that skips a file it cannot parse reports that file's sensors as *undeclared* rather than *unread*: a clean bill of health for every board the file describes.

**A threshold's name is free text; its `Direction` decides.** The 16,383 thresholds spell their names fifteen ways – `upper critical`, `higher critical`, `HardShutdown`, and `lower non-recoverable` beside `lower non recoverable` among them – where the documented example shows four. The schema requires `Direction` and allows it two values, while a name may be any string, so it is `Direction` that says which side a threshold guards.

Each of the five makes a coverage check wrong in one direction or the other. It reports a healthy board as missing sensors, which teaches its users to ignore it; or it reports a board as complete because it never built the expectation that would have failed, and nothing downstream can notice an expectation that was never built.

## Two thresholds that contradict themselves

On the Yosemite V2 and Yosemite V3P5 baseboards, the hot-swap controller's `temp1` threshold is named `upper critical` and declared `Direction: less than`. The sensor daemon never reads a threshold's name, so as written each is a critical *low* threshold, at 105 °C and 55 °C: one that asserts whenever the part is at or below that temperature. Across all 16,383 thresholds these are the only two whose name contradicts their direction. Both are valid against the schema, which constrains each field of a threshold on its own and relates none to another. Neither board is built upstream any more: on 16 May 2025 `openbmc/openbmc` removed both machine layers, and the two configurations stayed. What they show is the shape the schema lets through, not a fault on a board in use. Filed upstream as [`entity-manager` issue #38](https://github.com/openbmc/entity-manager/issues/38).

## Counts drift; shapes do not

Nine weeks earlier, at revision `0ada048` (committed 14 August 2026), the same reader counted 349 files, 9,424 declarations, 2,069 of them not sensors, and 15,860 thresholds, with the same two contradictions. Most counts moved, and every shape held. So a count is half a claim, and the other half is the revision it was taken at. The tool now prints both:

```
pip install bmc-sensor-audit==0.3.19
git clone https://github.com/openbmc/entity-manager
bmc-sensor-audit census entity-manager/configurations
```

`census` reads the corpus exactly as the tool reads a board, and names the commit it counted, dated by when it was committed, and whether any file under the directory differs from that commit.

## End to end, on firmware nobody wrote for it

The corpus is what boards declare. The check runs against firmware: the bletchley board's upstream image, built by OpenBMC's continuous integration on 15 August 2026, booted under the QEMU 10.2.1 emulator and walked over Redfish on 18 August. An emulator has no manufacturing data, so the board appeared only after a synthetic FRU record was written into its EEPROM. The machine reported 28 sensors on 3 chassis.

Compared with the board's three upstream configuration files, the released tool counts 86 declared sensors: 28 matched and reading, 58 declared and not reported at all, and none reported that nothing declares. It exits 1. It does not report a clean board.

Two things in that result matter beyond this board. Every one of the 28 matches needed a normalised name – the configuration declares `IMON_FAN0` and the machine reports `IMON FAN0` – and the tool says of each pairing that it was not exact, for a person to confirm. And the 58 absences are, one for one, devices the emulated board does not have: the rails of its hot-swap controllers and current monitors (46), its fans' tachometers (8), and its front panel's humidity and temperature sensor, declared twice, once for each of two parts (4). On a physical board the same 58 names are the list to check: each one is reporting, or is missing for a reason someone should know.

The witherspoon board's OpenBMC 2.9.0 release image, published in 2021, is the same trap facing the other way. Its modern `Sensors` collection is empty, while its older `Thermal` document carries two temperatures and four fans, each with a reading. A reader that knows only the modern collection walks this machine and finds no sensor, no reading, and so no alarm. A current image can be the same case for the opposite reader: `bmcweb` still carries the older documents' handlers, behind a build option that is off by default and whose own description says it "will be removed June 2026" – at revision `7da5af6` it is still there and still off.

Both recordings ship with the tool, so the bletchley result runs from a clone, with no hardware:

```
git clone --depth 1 --branch v0.3.19 https://github.com/james-sheen/bmc-sensor-audit
cd bmc-sensor-audit/tests/fixtures
bmc-sensor-audit coverage --config upstream/meta/bletchley --walk walk_qemu_bletchley.json
```

## What emulation cannot show

It shows that the check runs end to end on firmware nobody wrote for it, that it names every declared sensor a machine does not report rather than passing over it, and that it does not call a board clean while any of them is missing. It cannot show what a physical board reports. The emulator models a subset of each board's devices, so its absences are facts about the emulator, and no physical board has been captured yet. That is the report's first ask: one rack, on non-commercial terms, to run the check against real hardware.

---

The report – the corpus at two revisions, these walks, the chain from a factory's acceptance certificate to the buyer's fleet, and the claims ledger behind every figure – is at `github.com/james-sheen/absent-is-not-healthy`, DOI [10.5281/zenodo.23585862](https://doi.org/10.5281/zenodo.23585862). The tool is [`bmc-sensor-audit`](https://pypi.org/project/bmc-sensor-audit/), Apache-2.0.

The report, its posts and its tools are listed at [github.com/james-sheen](https://github.com/james-sheen).
