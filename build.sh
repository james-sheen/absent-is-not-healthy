#!/usr/bin/env bash
# Build the technical report and its brief as PDFs, from their Markdown source: pandoc to Typst, Typst to PDF.
#
#     build.sh [OUT_DIR]        (default: a fresh directory under ${TMPDIR:-/tmp}; never this tree)
#
# The tools come from PyPI into a virtualenv of their own, pinned, so a build needs no system package and
# builds the same next month: pypandoc_binary carries pandoc itself, typst carries the compiler.
#
# Three of the rules are mechanical, so the build refuses a source that breaks them rather than leaving them to
# a read-through: the engine is named in section 6 and not before; no internal reference -- a ticket id or a
# repository nickname -- reaches a document that ships; and the brief states no figure the report does not,
# since every sentence in it is one the report and its ledger already carry.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$(mktemp -d "${TMPDIR:-/tmp}/report-build.XXXXXX")}"
VENV="${REPORT_BUILD_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/arbiter-report-build}"
PINS=("pypandoc_binary==1.17" "typst==0.15.0")

if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" -c "import importlib.metadata as m, sys
sys.exit(0 if (m.version('pypandoc_binary'), m.version('typst')) == ('1.17', '0.15.0') else 1)" 2>/dev/null; then
  python3 -m virtualenv -q "$VENV"
  "$VENV/bin/pip" install -q --disable-pip-version-check "${PINS[@]}"
fi
mkdir -p "$OUT"

PYTHONDONTWRITEBYTECODE=1 "$VENV/bin/python" - "$HERE" "$OUT" <<'PY'
import pathlib, re, sys
import pypandoc, typst

here, out = map(pathlib.Path, sys.argv[1:3])
refused = []
for doc in ("absent-is-not-healthy", "brief"):
    text = (here / f"{doc}.md").read_text(encoding="utf-8")
    before_six = text.split("\n# 6.", 1)[0] if "\n# 6." in text else text
    if doc == "absent-is-not-healthy" and re.search(r"arbiter[-_]engine", before_six, re.IGNORECASE):
        refused.append(f"{doc}.md names the engine before section 6")
    for m in re.finditer(r"\b(?:CD|DDC)-\d+\b|\b(?i:repo(?:sitory)?)\s*#\s*\d+|\b(?:MEM[O]|RES[P])\b|\bB[Q]\d+\b", text):   # spelled so this line is not one of them
        line = text.count("\n", 0, m.start()) + 1
        refused.append(f"{doc}.md:{line}: internal reference {m.group(0)!r}")
def figures(text):
    """Every figure in a document's text, past its front matter: 1,260, 105, 0.2.39, 2025. A DOI is an identifier,
    not a figure, and the report carries its own on its title page, in the front matter."""
    body = text.split("\n---\n", 1)[1] if text.startswith("---\n") else text
    return set(re.findall(r"\d+(?:[.,]\d+)*", re.sub(r"\b10\.\d{4,9}/\S+", "", body)))
stated = figures((here / "absent-is-not-healthy.md").read_text(encoding="utf-8"))
for figure in sorted(figures((here / "brief.md").read_text(encoding="utf-8")) - stated):
    refused.append(f"brief.md states {figure!r}, which the report does not")
if refused:
    print("REFUSED:", *refused, sep="\n  ")
    sys.exit(1)
for doc in ("absent-is-not-healthy", "brief"):
    typ, pdf = out / f"{doc}.typ", out / f"{doc}.pdf"
    pypandoc.convert_file(str(here / f"{doc}.md"), "typst", outputfile=str(typ), extra_args=["--standalone"])
    data = typst.compile(str(typ))
    pdf.write_bytes(data)
    pages = len(re.findall(rb"/Type\s*/Page\b(?!s)", data))
    print(f"built {pdf} ({pages} page{'s' if pages != 1 else ''})")
PY
