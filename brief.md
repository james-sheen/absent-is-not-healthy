---
title: "Absent is not healthy"
subtitle: "Checking what a BMC declares against what it reports"
author: "James Sheen · The Arbiter Project"
date: "Brief, version 1.0, 2026-10-23"
lang: en
---

**The problem.** A server's baseboard management controller (BMC) reports its sensors, and a reader that waits
for a reading to cross a line learns nothing from a sensor that reports nothing: silence reads as health. The
report this brief summarises checks what a board's configuration declares against what its firmware reports --
on OpenBMC's public configuration corpus and on upstream firmware -- and follows the result into the documents a
factory hands a buyer. Written for those who build, buy and run servers at fleet scale, it is about three ways
a machine can be read as healthy when the true answer is *not known*: a sensor that does not report looks like one that sees nothing wrong; a declared limit can contradict
itself and pass the schema; and a check that could not run can exit 0.

**What we found.**

1. **Absence has to be read right before it can be reported.** Across 362 configuration files, about three in
   ten declarations are not sensors at all, 1,260 declared rails carry no threshold to build them from, and 823
   names are templates. Each makes a naive coverage check report a healthy board as broken, or a broken one as
   complete (section 3).
2. **On upstream firmware, a reader that waits for a crossing sees a healthy machine.** An emulated current
   board reports 28 of its 86 declared sensors, and a 2021 firmware image serves none through its modern
   interface at all; a reader that waits for a reading to cross a line sees nothing wrong in either. The released
   audit tool names the other 58 and does not call the board clean (section 4).
3. **Two declared limits contradict themselves and pass the schema.** Two boards' hot-swap controllers declare a
   threshold named *upper critical* as a low one, so as written each asserts whenever the part is at or below
   105 °C or 55 °C. Neither board is built upstream any more, so what they show is the shape the schema lets
   through, not a fault in use (section 3). Filed upstream as [`entity-manager` issue #38](https://github.com/openbmc/entity-manager/issues/38).

**The moved line.** A firmware update that moves a threshold looks exactly like a recovery unless the line is
declared and dated. The detection engine underneath the audit says how each closed case closed: on the
reading, the line or both, or because the line was withdrawn or the unit retired. Its evidence so far is public
data, not hardware (appendix B).

**What an acceptance certificate should state.** A certificate that shows only what was checked reads as a
clean bill of health for every question nobody asked. So it should state, on the page a person reads and not
only in the record behind it:

- the denominator: how many checks, over how many sensors;
- declared against present, naming every declared sensor that did not report;
- what was not judged, each with its reason;
- the measurement behind each finding;
- which capture it was judged from, by content, and whether that was checked.

It does not attest that the document is genuine, since nothing in it is signed; that the declaration it was
judged against is right; that conformance or fault-injection tests ran; or anything about time, since one
capture judges one moment (section 5).

**What we ask.**

- **One rack**, on non-commercial terms, to run this chain against real hardware: the coverage check on
  physical boards, a buyer's captures across time and firmware, and a certificate for a unit that was really
  built. Each is an exhibit the report says it lacks.
- **Upstream review** of the two contradictory thresholds and of the checks that found them, filed as
  [`entity-manager` issue #38](https://github.com/openbmc/entity-manager/issues/38).
- **Standards feedback**, through OCP Hardware Management: on what an acceptance certificate should state on its
  page, and on reporting absence as a result of its own rather than as silence.

**Who is asking.** James Sheen, for The Arbiter Project. The five tools in the chain --
`bmc-sensor-audit`, `presence-audit`, `odm-cert-generator`, `fleet-sensor-baseline` and `arbiter-engine` -- are
released on PyPI under Apache-2.0.

**Where the evidence is.** The report: *Absent is not healthy: checking what a BMC declares against what it
reports*, The Arbiter Project, DOI [10.5281/zenodo.23585862](https://doi.org/10.5281/zenodo.23585862). Its repository, linked from
that DOI's record, holds the report's source and the
claims ledger behind it: every figure above, with the source it rests on and a check that holds it, run against
upstream at the revisions the report names and against each tool as released. Everything reproduces from
released versions, with no hardware.

*This brief is licensed CC BY 4.0.*
