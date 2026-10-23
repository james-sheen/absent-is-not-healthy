# Absent is not healthy

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23585862.svg)](https://doi.org/10.5281/zenodo.23585862)
[![All versions](https://zenodo.org/badge/DOI/10.5281/zenodo.23585861.svg)](https://doi.org/10.5281/zenodo.23585861)

*Checking what a BMC declares against what it reports.* A technical report from The Arbiter Project.

A baseboard management controller reads a server's sensors and reports them to whatever watches the machine, and
a sensor that does not report looks exactly like one that sees nothing wrong. The report checks what a board's
configuration declares against what the running system reports -- on the public OpenBMC configuration corpus and
on upstream firmware -- and follows the result from a factory's acceptance certificate to the buyer's fleet.

**Versions.** Each version is a tagged release here, with its PDF, archived on Zenodo with a DOI of its own.

## What is here

| File | What it is |
|---|---|
| `absent-is-not-healthy.md` | the report's source |
| `brief.md` | the two-page brief |
| `claims.md` | every load-bearing figure in the report, with its source and the check that holds it |
| `measure_corpus.py`, `check_consumer.py`, `check_layers.py`, `check_appendix.py`, `check_firmware.py`, `check_chain.py`, `check_walk.py`, `check_text.py` | the checks behind the figures, run again at the versions and revisions the report names |
| `appendix-b/` | the two case studies behind section 6, runnable on the released engine |
| `build.sh` | the PDFs, from this source |

## Building the PDFs

    bash build.sh [OUT_DIR]

pandoc and Typst come from PyPI, pinned, into a virtual environment of their own (`~/.cache/arbiter-report-build`),
so nothing is installed system-wide. It needs Python 3.10 or later and `virtualenv`.

## Checking the figures

Each row of `claims.md` names the source of one figure and the check that holds it: a command to run, or a file
and the text it must hold. The commands fetch each upstream source at the revision the report names --
`entity-manager`, `dbus-sensors`, `bmcweb`, QEMU -- and install each tool at the version it names from PyPI, into an
environment of its own, because a figure is a claim about one version of the thing it describes.

## Running the case studies

`appendix-b/README.md`: with `arbiter-engine` 0.2.39 from PyPI, each case runs, and its scorer holds the run to the
answers written before it ran and fails on any departure.

## Licences

The report's text is CC BY 4.0 (`LICENSE`). The code -- the build, the measurements and appendix B's scripts -- is
Apache-2.0 (`LICENSE-CODE`, and `appendix-b/LICENSE`). The data in appendix B are United States government works.

## How to cite

Cite the report by its DOI, [10.5281/zenodo.23585862](https://doi.org/10.5281/zenodo.23585862), which names the version you read.
Each version is deposited on Zenodo by hand and carries its own DOI, on its title page and in `CITATION.cff`, which
GitHub's *Cite this repository* reads. Link this repository for what the DOI cannot hold: the source, the ledger
and the case studies, at the tag of the version you cite.
