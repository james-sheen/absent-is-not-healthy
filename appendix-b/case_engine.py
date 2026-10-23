"""Which engine a case study's offline run uses: the release installed from PyPI, or the engine in a source tree.

    run_walks.py --engine published   `arbiter_engine`, as `pip install arbiter-engine` installs it
    run_walks.py --engine tree        the engine in the source tree, where there is one

The walk the runners call, `walks.py`, is standard library only and takes the engine module as an argument, so the
published engine runs the same walk, loaded by path, with nothing of a source tree imported. A case's figures then
reproduce on a released version -- the rule a report citing them keeps. Where `walks.py` sits beside this file it is
the one loaded; the source tree's own copy otherwise.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Tuple

HERE = Path(__file__).resolve().parent

try:                                    # present only in the source tree, and never shipped with a case
    import case_engine_tree as _tree
except ImportError:
    _tree = None

ENGINES = ("published", "tree") if _tree else ("published",)
DEFAULT = "tree" if _tree else "published"
WALKS = HERE / "walks.py" if (HERE / "walks.py").is_file() or _tree is None else _tree.WALKS


def load(which: str) -> Tuple[ModuleType, ModuleType, Any]:
    """`(api, walks, InMemoryObservationHistory)` from the engine named."""
    if which == "published":
        from arbiter_engine import api
        from arbiter_engine.history.observation import InMemoryObservationHistory
        spec = importlib.util.spec_from_file_location("walks", WALKS)
        walks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(walks)
        return api, walks, InMemoryObservationHistory
    if which == "tree" and _tree is not None:
        return _tree.load()
    raise ValueError(f"engine {which!r}: one of {ENGINES}")


def describe(which: str, api: ModuleType) -> str:
    """The engine a run used, as its log should say it."""
    if which == "published":
        from importlib.metadata import version
        return f"arbiter-engine {version('arbiter-engine')} ({api.__file__})"
    return f"the engine in the source tree ({api.__file__})"
